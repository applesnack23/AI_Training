"""remove_tag.py — TensorBoard events 파일에서 특정 항목(기본 time/fps)만 지우기 (tensorflow 없이)
   python remove_tag.py <events 파일> [<out 파일>] [--tag time/fps]
   out 을 안 주면 같은 자리에 덮어씀 (원본은 .bak 으로 남김)"""
import struct, sys, shutil

def _table():
    t = []
    for i in range(256):
        c = i
        for _ in range(8): c = (c >> 1) ^ 0x82F63B78 if c & 1 else c >> 1
        t.append(c)
    return t
T = _table()
def crc32c(b):
    c = 0xFFFFFFFF
    for x in b: c = T[(c ^ x) & 0xFF] ^ (c >> 8)
    return c ^ 0xFFFFFFFF
def masked(b):
    c = crc32c(b); return (((c >> 15) | (c << 17)) + 0xA282EAD8) & 0xFFFFFFFF

def varint(b, i):
    r = s = 0
    while True:
        c = b[i]; i += 1; r |= (c & 0x7f) << s; s += 7
        if c < 0x80: return r, i
def enc_varint(n):
    o = bytearray()
    while True:
        x = n & 0x7f; n >>= 7
        if n: o.append(x | 0x80)
        else: o.append(x); return bytes(o)
def fields(b):
    i = 0
    while i < len(b):
        s = i; k, i = varint(b, i); f, t = k >> 3, k & 7
        if t == 0: v, i = varint(b, i)
        elif t == 1: v = b[i:i + 8]; i += 8
        elif t == 5: v = b[i:i + 4]; i += 4
        elif t == 2: n, i = varint(b, i); v = b[i:i + n]; i += n
        else: raise ValueError(t)
        yield f, t, v, b[s:i]

def records(d):
    i = 0
    while i < len(d):
        hdr = d[i:i + 8]; n = struct.unpack('<Q', hdr)[0]
        assert struct.unpack('<I', d[i + 8:i + 12])[0] == masked(hdr), 'header crc'
        rec = d[i + 12:i + 12 + n]
        assert struct.unpack('<I', d[i + 12 + n:i + 16 + n])[0] == masked(rec), 'data crc'
        yield rec; i += 16 + n

def strip(rec, tag):
    """Event 안 Summary 의 Value 중 tag 인 것 빼기. 남는 값이 없으면 None"""
    out = bytearray(); had_summary = False; removed = 0
    for f, t, v, raw in fields(rec):
        if f == 5 and t == 2:
            had_summary = True; keep = bytearray()
            for f2, t2, v2, raw2 in fields(v):
                if f2 == 1:
                    tg = next((v3.decode() for f3, t3, v3, _ in fields(v2) if f3 == 1), None)
                    if tg == tag: removed += 1; continue
                keep += raw2
            if not keep: return None, removed
            out += enc_varint((5 << 3) | 2) + enc_varint(len(keep)) + keep
        else:
            out += raw
    return bytes(out), removed

def write(recs):
    o = bytearray()
    for r in recs:
        h = struct.pack('<Q', len(r)); o += h + struct.pack('<I', masked(h)) + r + struct.pack('<I', masked(r))
    return bytes(o)

if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    tag = sys.argv[sys.argv.index('--tag') + 1] if '--tag' in sys.argv else 'time/fps'
    a = [x for x in a if x != tag]
    src = a[0]; dst = a[1] if len(a) > 1 else src
    d = open(src, 'rb').read(); keep = []; n_rm = 0; n_in = 0
    for r in records(d):
        n_in += 1; s, k = strip(r, tag); n_rm += k
        if s is not None: keep.append(s)
    if dst == src: shutil.copy2(src, src + '.bak')
    open(dst, 'wb').write(write(keep))
    print(f'{src}: 기록 {n_in} 개 중 "{tag}" {n_rm} 개 지움 → {len(keep)} 개 남김')
