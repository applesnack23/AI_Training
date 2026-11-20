# -*- coding: utf-8 -*-
"""twin_sim.py — 파이썬으로 만든 간단한 컨베이어 디지털 트윈 (2D 화면)

실행 순서
  1) 먼저 Python 프로그램(rule_run.py · ai_run.py · 학습)을 실행
     → Modbus 서버 127.0.0.1:1502 가 뜬다
  2) 다른 터미널에서
       python twin_sim.py           (화면 있음)
       python twin_sim.py --fast    (강화학습 때: 5 배 빠르게)
       python twin_sim.py --nogui   (화면 없이)

주고받는 값 (modbus_server.py 와 같음, 20 ms 마다)
  HR0  ← 트윈이 씀  : bit0 센서 A, bit1 센서 B, bit2 박스 사라짐
  HR10 → 트윈이 읽음: bit0 LEFT, bit1 RIGHT, bit2 RESET
"""
import socket, struct, sys, threading, time

HOST, PORT, UNIT = "127.0.0.1", 1502, 1
DT = 0.02                       # 20 ms 마다 한 번
SPEED = 60.0                    # 벨트 속도 mm/s
if "--fast" in sys.argv:
    SPEED *= 5
BELT, A_POS, B_POS = 148, 9, 140   # 벨트 길이 · 센서 A · B 위치 (mm)
BOX, SEE = 30, 20               # 박스 길이, 센서가 보는 거리(중심 ±)
LOST_L, LOST_R, START = -22, 170, 9  # 떨어지는 곳, 리셋 위치

# ---------------- 컨베이어 계산 ----------------
box = {"x": START, "lost": 0}

def step(cmd, dt):
    """명령(HR10)을 받아 박스를 움직이고 HR0 값을 돌려준다"""
    if cmd & 4:                 # RESET: 박스를 센서 A 자리로
        box["x"], box["lost"] = START, 0
    elif not box["lost"]:
        if cmd & 2:             # RIGHT → B 쪽
            box["x"] += SPEED * dt
        elif cmd & 1:           # LEFT  → A 쪽
            box["x"] -= SPEED * dt
        if box["x"] < LOST_L or box["x"] > LOST_R:
            box["lost"] = 1
    if box["lost"]:
        return 4
    a = abs(box["x"] - A_POS) <= SEE
    b = abs(box["x"] - B_POS) <= SEE
    return int(a) | (int(b) << 1)

# ---------------- Modbus TCP (클라이언트) ----------------
class Modbus:
    def __init__(self):
        self.s = None
        self.tid = 0

    def connect(self):
        try:
            self.s = socket.create_connection((HOST, PORT), timeout=1)
            return True
        except OSError:
            self.s = None
            return False

    def _ask(self, pdu):
        self.tid = (self.tid + 1) & 0xFFFF
        head = struct.pack(">HHHB", self.tid, 0, len(pdu) + 1, UNIT)
        self.s.sendall(head + pdu)
        n = struct.unpack(">HHHB", self.s.recv(7))[2] - 1
        return self.s.recv(n)

    def read(self, addr):       # FC3: 레지스터 하나 읽기
        r = self._ask(struct.pack(">BHH", 3, addr, 1))
        return struct.unpack(">H", r[2:4])[0]

    def write(self, addr, val):  # FC6: 레지스터 하나 쓰기
        self._ask(struct.pack(">BHH", 6, addr, val))

mb = Modbus()
state = {"cmd": 0, "hr0": 0, "ok": False, "trying": False, "last": 0.0}

def _try_connect():             # 화면이 멈추지 않게 따로 연결 시도
    state["ok"] = mb.connect()
    state["trying"] = False

def tick():
    """20 ms 마다: HR10 읽기 → 박스 움직이기 → HR0 쓰기"""
    if not state["ok"]:
        now = time.time()       # 연결 시도는 1 초에 한 번만
        if not state["trying"] and now - state["last"] >= 1.0:
            state["trying"], state["last"] = True, now
            threading.Thread(target=_try_connect, daemon=True).start()
        return
    try:
        state["cmd"] = mb.read(10)
        state["hr0"] = step(state["cmd"], DT)
        mb.write(0, state["hr0"])
    except OSError:
        state["ok"] = False

# ---------------- 화면 (tkinter, 2D) ----------------
NAMES = {0: "STOP", 1: "LEFT", 2: "RIGHT", 4: "RESET"}

def message():
    if not state["ok"]:
        return f"연결 기다리는 중 — 서버({HOST}:{PORT})를 먼저 실행"
    c, h = state["cmd"], state["hr0"]
    return (f"연결됨   명령 HR10 = {c} ({NAMES.get(c, '?')})   "
            f"센서 HR0 = {h} (A={h & 1}, B={h >> 1 & 1}, "
            f"사라짐={h >> 2 & 1})")

def gui():
    import tkinter as tk
    S, X0, Y0 = 3.5, 120, 140   # 1 mm = 3.5 픽셀
    px = lambda mm: X0 + mm * S
    win = tk.Tk()
    win.title("컨베이어 디지털 트윈 (twin_sim.py)")
    cv = tk.Canvas(win, width=760, height=260, bg="white")
    cv.pack()
    cv.create_rectangle(px(0), Y0, px(BELT), Y0 + 24, fill="#555")
    for x in (0, BELT):         # 양쪽 롤러
        cv.create_oval(px(x) - 14, Y0 - 2, px(x) + 14, Y0 + 26,
                       fill="#ccc")
    cv.create_text(px(0), Y0 + 45, text="A 쪽 (LEFT)")
    cv.create_text(px(BELT), Y0 + 45, text="B 쪽 (RIGHT)")
    sens = []
    for x, name in ((A_POS, "A"), (B_POS, "B")):
        sens.append(cv.create_oval(px(x) - 12, 40, px(x) + 12, 64,
                                   fill="white", width=2))
        cv.create_text(px(x), 28, text="센서 " + name)
        cv.create_line(px(x), 64, px(x), Y0, dash=(4, 4), fill="red")
    boxid = cv.create_rectangle(0, 0, 0, 0, fill="#e8c07a",
                                outline="#8a5a10", width=2)
    info = cv.create_text(380, 225, font=("맑은 고딕", 12))

    def loop():
        tick()
        h = state["hr0"]
        for k, o in enumerate(sens):
            cv.itemconfig(o, fill="lime" if h >> k & 1 else "white")
        if box["lost"]:
            cv.coords(boxid, 0, 0, 0, 0)
        else:
            cv.coords(boxid, px(box["x"] - BOX / 2), Y0 - 60,
                      px(box["x"] + BOX / 2), Y0)
        cv.itemconfig(info, text=message())
        win.after(int(DT * 1000), loop)
    loop()
    win.mainloop()

if __name__ == "__main__":
    if "--nogui" in sys.argv:
        print("twin_sim.py — 화면 없이 실행 (Ctrl+C 로 끝)")
        while True:
            tick()
            time.sleep(DT)
    else:
        gui()
