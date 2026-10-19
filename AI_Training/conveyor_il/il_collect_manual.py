"""
IL Data Collection - Modbus TCP Server + Keyboard Expert

Unity (Modbus TCP Client) 가 이 서버에 접속합니다.
  - Unity -> Python : HR0  (센서)
  - Python -> Unity : HR10 (모터 명령)

키보드로 모터를 조작하면서 (센서 상태, Expert Action) 을 수집합니다.
  A : LEFT  (왼쪽 이동)
  S : STOP  (멈춤)
  D : RIGHT (오른쪽 이동)
  X : 저장 후 종료
  Q : 저장 후 종료 (Ctrl+C 도 저장 후 종료)

Windows (msvcrt) / Linux·macOS (termios) 모두 지원합니다.
Enter 없이 키를 바로 인식하므로 터미널(cmd, PowerShell 등)에서 실행하세요.
"""

import asyncio
import sys
import threading
import time
from pathlib import Path

import pandas as pd
from pymodbus.server import ModbusTcpServer
from pymodbus.simulator import (
    SimData,
    SimDevice,
    DataType,
)


# ============================================================
# Path
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "il_dataset.csv"


# ============================================================
# Modbus
# ============================================================

MODBUS_IP = "127.0.0.1"
MODBUS_PORT = 1502
DEVICE_ID = 1
HR_SIZE = 20

HR_SENSOR = 0
HR_COMMAND = 10

FC_HOLDING = 3


# ============================================================
# HR0 Bit
# ============================================================

BIT_SENSOR01 = 0
BIT_SENSOR02 = 1
BIT_WORKPIECE_LOST = 2


# ============================================================
# HR10 Bit
# ============================================================

BIT_LEFT = 0
BIT_RIGHT = 1


# ============================================================
# Action
# ============================================================

ACTION_STOP = 0
ACTION_LEFT = 1
ACTION_RIGHT = 2

ACTION_NAMES = {
    ACTION_STOP: "STOP",
    ACTION_LEFT: "LEFT",
    ACTION_RIGHT: "RIGHT",
}

KEY_ACTIONS = {
    "a": ACTION_LEFT,
    "s": ACTION_STOP,
    "d": ACTION_RIGHT,
}

QUIT_KEYS = ("x", "q", "\x03")      # x, q, Ctrl+C


# ============================================================
# Sampling
# ============================================================

SAMPLE_TIME = 0.05


# ============================================================
# Action -> HR10
# ============================================================

def encode_action(action):

    if action == ACTION_LEFT:
        return 1 << BIT_LEFT

    if action == ACTION_RIGHT:
        return 1 << BIT_RIGHT

    return 0


# ============================================================
# Keyboard (Enter 없이 1글자 입력)
# ============================================================

def _keyboard_loop_windows(on_key, stop_event):

    import msvcrt

    while not stop_event.is_set():

        if not msvcrt.kbhit():
            time.sleep(0.02)
            continue

        ch = msvcrt.getwch()

        # 방향키/F키 등 확장키는 2바이트 -> 두 번째 바이트 버림
        if ch in ("\x00", "\xe0"):
            msvcrt.getwch()
            continue

        on_key(ch.lower())


def _keyboard_loop_posix(on_key, stop_event):

    import select
    import termios
    import tty

    if not sys.stdin.isatty():
        print("[ERROR] 터미널에서 직접 실행해주세요.", flush=True)
        stop_event.set()
        return

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:

        tty.setcbreak(fd)

        while not stop_event.is_set():

            ready, _, _ = select.select([sys.stdin], [], [], 0.1)

            if not ready:
                continue

            on_key(sys.stdin.read(1).lower())

    finally:

        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def keyboard_worker(state, lock, stop_event):

    def on_key(key):

        if key in QUIT_KEYS:
            stop_event.set()
            return

        action = KEY_ACTIONS.get(key)

        if action is None:
            return

        with lock:
            state["action"] = action

        print(f"[EXPERT] {ACTION_NAMES[action]}", flush=True)

    try:

        if sys.platform.startswith("win"):
            _keyboard_loop_windows(on_key, stop_event)
        else:
            _keyboard_loop_posix(on_key, stop_event)

    except Exception as e:

        print(f"[ERROR] Keyboard: {e}", flush=True)
        stop_event.set()


# ============================================================
# Save
# ============================================================

def save_dataset(data):

    if len(data) == 0:

        print()
        print("[ERROR] No data collected.")
        return

    df = pd.DataFrame(
        data,
        columns=[
            "Sensor01",
            "Sensor02",
            "LastSensor",
            "Action",
        ],
    )

    df.to_csv(
        DATASET_PATH,
        index=False,
    )

    print()
    print("============================================")
    print(" IL DATASET SAVED")
    print("============================================")
    print()

    print(f"Total Samples : {len(df)}")

    print()
    print("Action Count")
    print("--------------------------------------------")

    for action in [
        ACTION_STOP,
        ACTION_LEFT,
        ACTION_RIGHT,
    ]:

        count = int(
            (df["Action"] == action).sum()
        )

        print(f"{ACTION_NAMES[action]:5s} : {count}")

    print("--------------------------------------------")
    print()

    print(f"Saved : {DATASET_PATH}")
    print()


# ============================================================
# Main
# ============================================================

async def main():

    print()
    print("============================================")
    print(" IL DATA COLLECTION (MODBUS TCP SERVER)")
    print("============================================")
    print()

    print(f"IP        : {MODBUS_IP}")
    print(f"PORT      : {MODBUS_PORT}")
    print(f"DEVICE ID : {DEVICE_ID}")
    print()
    print("HR0  : Unity -> Python (Sensor01 / Sensor02 / Lost)")
    print("HR10 : Python -> Unity (bit0 LEFT / bit1 RIGHT)")
    print()
    print("[KEY] A = LEFT   S = STOP   D = RIGHT   X/Q = SAVE & QUIT")
    print()

    # ========================================================
    # Server
    # ========================================================

    device = SimDevice(
        id=DEVICE_ID,
        simdata=[
            SimData(
                address=0,
                count=HR_SIZE,
                values=0,
                datatype=DataType.REGISTERS,
            ),
        ],
    )

    server = ModbusTcpServer(
        context=device,
        address=(
            MODBUS_IP,
            MODBUS_PORT,
        ),
    )

    stop_event = threading.Event()
    lock = threading.Lock()
    state = {"action": ACTION_STOP}

    data = []

    # 초기에는 Sensor01에서 출발한다고 가정
    last_sensor = 1

    previous_state = None
    next_status = 100
    server_started = False

    try:

        # 포트(1502)가 이미 사용 중이면 여기서 예외 발생
        await server.serve_forever(background=True)
        server_started = True

        print(
            f"[MODBUS] Server Started "
            f"{MODBUS_IP}:{MODBUS_PORT}"
        )
        print("[MODBUS] Unity 접속 대기 중... (Unity에서 통신 시작)")
        print()

        threading.Thread(
            target=keyboard_worker,
            args=(state, lock, stop_event),
            daemon=True,
        ).start()

        while not stop_event.is_set():

            with lock:
                action = state["action"]

            # =================================================
            # Expert Command -> HR10
            # =================================================

            await server.async_setValues(
                DEVICE_ID,
                FC_HOLDING,
                HR_COMMAND,
                [encode_action(action)],
            )

            # =================================================
            # Sensor <- HR0
            # =================================================

            values = await server.async_getValues(
                DEVICE_ID,
                FC_HOLDING,
                HR_SENSOR,
                count=1,
            )

            hr0 = int(values[0]) if values else 0

            sensor01 = (hr0 >> BIT_SENSOR01) & 1
            sensor02 = (hr0 >> BIT_SENSOR02) & 1
            workpiece_lost = (hr0 >> BIT_WORKPIECE_LOST) & 1

            # =================================================
            # LastSensor
            # =================================================

            if sensor01 == 1:
                last_sensor = 1

            elif sensor02 == 1:
                last_sensor = 2

            # =================================================
            # Dataset
            #
            # Lost 상태는 정상 Expert 동작이 아니므로 제외
            # =================================================

            if workpiece_lost == 0:

                data.append([
                    sensor01,
                    sensor02,
                    last_sensor,
                    action,
                ])

            # =================================================
            # Console
            # =================================================

            current_state = (
                sensor01,
                sensor02,
                last_sensor,
                action,
                workpiece_lost,
            )

            if current_state != previous_state:

                print(
                    f"[COLLECT] "
                    f"S1={sensor01} "
                    f"S2={sensor02} "
                    f"Last={last_sensor} "
                    f"Expert={ACTION_NAMES[action]} "
                    f"Lost={workpiece_lost}",
                    flush=True,
                )

                previous_state = current_state

            if len(data) >= next_status:

                print(
                    f"[DATA] {len(data)} samples collected",
                    flush=True,
                )

                next_status += 100

            await asyncio.sleep(SAMPLE_TIME)

    except (KeyboardInterrupt, asyncio.CancelledError):

        print()
        print("[COLLECT] Collection stopped.")

    finally:

        stop_event.set()

        if server_started:

            try:
                # 종료 시 모터 정지
                await server.async_setValues(
                    DEVICE_ID,
                    FC_HOLDING,
                    HR_COMMAND,
                    [0],
                )
                await asyncio.sleep(0.1)

            finally:
                await server.shutdown()

        save_dataset(data)


# ============================================================
# Entry
# ============================================================

if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        pass
