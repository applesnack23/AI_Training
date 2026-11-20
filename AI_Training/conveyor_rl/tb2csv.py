"""tb2csv.py — TensorBoard events 파일 → CSV (tensorflow · tensorboard 없이)
   python tb2csv.py <events 파일> <out.csv>"""
import struct, sys, csv, collections

def varint(b, i):
    r = s = 0
    while True:
        c = b[i]; i += 1; r |= (c & 0x7f) << s; s += 7
        if c < 0x80: return r, i

def fields(b):
    i = 0
    while i < len(b):
        k, i = varint(b, i); f, t = k >> 3, k & 7
        if t == 0: v, i = varint(b, i)
        elif t == 1: v = b[i:i + 8]; i += 8
        elif t == 5: v = b[i:i + 4]; i += 4
        elif t == 2: n, i = varint(b, i); v = b[i:i + n]; i += n
        else: raise ValueError(t)
        yield f, t, v

def read(path):
    d = open(path, 'rb').read(); i = 0; rows = collections.defaultdict(dict)
    while i < len(d):
        n = struct.unpack('<Q', d[i:i + 8])[0]; rec = d[i + 12:i + 12 + n]; i += 12 + n + 4
        step = 0; summ = None
        for f, t, v in fields(rec):
            if f == 2: step = v
            if f == 5: summ = v
        if summ is None: continue
        for f, t, v in fields(summ):
            if f != 1: continue
            tag = None; val = None
            for f2, t2, v2 in fields(v):
                if f2 == 1: tag = v2.decode()
                if f2 == 2: val = struct.unpack('<f', v2)[0]
                if f2 == 8:                                      # tensor 형식 scalar
                    for f3, t3, v3 in fields(v2):
                        if f3 == 5 and t3 == 2 and len(v3) == 4: val = struct.unpack('<f', v3)[0]
                        if f3 == 5 and t3 == 5: val = struct.unpack('<f', v3)[0]
            if tag is not None and val is not None: rows[step][tag] = val
    return rows

if __name__ == '__main__':
    rows = read(sys.argv[1]); tags = sorted({t for r in rows.values() for t in r})
    with open(sys.argv[2], 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(['step'] + tags)
        for s in sorted(rows): w.writerow([s] + [f"{rows[s][t]:.6g}" if t in rows[s] else '' for t in tags])
    print(len(rows), 'rows', tags)
