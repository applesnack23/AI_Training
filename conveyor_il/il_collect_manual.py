"""Keyboard expert + Modbus TCP server, for PyModbus 3.16.1 on Linux."""

import asyncio
import select
import sys
import termios
import threading
import tty
from pathlib import Path

import pandas as pd
from pymodbus.server import ModbusTcpServer
from pymodbus.simulator import DataType, SimData, SimDevice

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "il_dataset.csv"

MODBUS_IP = "127.0.0.1"
MODBUS_PORT = 1502
DEVICE_ID = 1
HR_SENSOR = 0
HR_COMMAND = 10

BIT_SENSOR01 = 0
BIT_SENSOR02 = 1
BIT_WORKPIECE_LOST = 2
BIT_LEFT = 0
BIT_RIGHT = 1

ACTION_STOP = 0
ACTION_LEFT = 1
ACTION_RIGHT = 2
ACTION_NAMES = {0: "STOP", 1: "LEFT", 2: "RIGHT"}
SAMPLE_TIME = 0.05


def encode_action(action):
    if action == ACTION_LEFT:
        return 1 << BIT_LEFT
    if action == ACTION_RIGHT:
        return 1 << BIT_RIGHT
    return 0


def keyboard_worker(state, lock, stop_event):
    """Read a/d/s/q without Enter. Only works in a real Linux terminal."""
    if not sys.stdin.isatty():
        print("[ERROR] Run from an interactive terminal.", flush=True)
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
            key = sys.stdin.read(1).lower()
            if key in ("q", "\x03"):
                stop_event.set()
                break
            action = {"a": ACTION_LEFT, "d": ACTION_RIGHT,
                      "s": ACTION_STOP}.get(key)
            if action is not None:
                with lock:
                    state["action"] = action
                print(f"\n[EXPERT] {ACTION_NAMES[action]}", flush=True)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def save_dataset(data):
    if not data:
        print("\n[ERROR] No data collected. CSV not saved.")
        return

    df = pd.DataFrame(
        data,
        columns=["Sensor01", "Sensor02", "LastSensor", "Action"],
    )
    df.to_csv(DATASET_PATH, index=False)
    print("\n============================================")
    print(" IL DATASET SAVED")
    print("============================================")
    print(f"Total Samples : {len(df)}")
    print("Action Count")
    print("--------------------------------------------")
    for action in (ACTION_STOP, ACTION_LEFT, ACTION_RIGHT):
        count = int((df["Action"] == action).sum())
        print(f"{ACTION_NAMES[action]:5s} : {count}")
    print("--------------------------------------------")
    print(f"Saved : {DATASET_PATH}\n")


async def main():
    # Holding registers 0..49; no address offset is needed with SimData.
    device = SimDevice(
        DEVICE_ID,
        SimData(0, datatype=DataType.REGISTERS, values=[0] * 50),
    )
    server = ModbusTcpServer(
        device,
        address=(MODBUS_IP, MODBUS_PORT),
    )

    stop_event = threading.Event()
    lock = threading.Lock()
    state = {"action": ACTION_STOP}
    data = []
    last_sensor = 1
    previous_state = None
    next_status = 100
    server_started = False

    print("\n============================================")
    print(" IL MANUAL EXPERT + MODBUS TCP SERVER")
    print("============================================")
    print(f"[MODBUS] {MODBUS_IP}:{MODBUS_PORT} (device_id={DEVICE_ID})")
    print("[KEY] A=LEFT  D=RIGHT  S=STOP  Q=SAVE & QUIT")
    print("[MAP] HR0=Sensors, HR10=Expert Command\n")

    try:
        # Raises an error if port 1502 is already in use.
        await server.serve_forever(background=True)
        server_started = True
        print("[MODBUS] Server listening.", flush=True)

        threading.Thread(
            target=keyboard_worker,
            args=(state, lock, stop_event),
            daemon=True,
        ).start()

        while not stop_event.is_set():
            with lock:
                action = state["action"]

            # Function code 3 = holding register datastore.
            await server.async_setValues(
                DEVICE_ID, 3, HR_COMMAND, [encode_action(action)]
            )
            hr0 = int((await server.async_getValues(
                DEVICE_ID, 3, HR_SENSOR, count=1
            ))[0])

            sensor01 = (hr0 >> BIT_SENSOR01) & 1
            sensor02 = (hr0 >> BIT_SENSOR02) & 1
            workpiece_lost = (hr0 >> BIT_WORKPIECE_LOST) & 1

            if sensor01:
                last_sensor = 1
            elif sensor02:
                last_sensor = 2

            # Ignore workpiece-lost samples.
            if not workpiece_lost:
                data.append([sensor01, sensor02, last_sensor, action])

            current_state = (
                sensor01, sensor02, last_sensor, action, workpiece_lost
            )
            if current_state != previous_state:
                print(
                    f"[COLLECT] S1={sensor01} S2={sensor02} "
                    f"Last={last_sensor} Expert={ACTION_NAMES[action]} "
                    f"Lost={workpiece_lost}",
                    flush=True,
                )
                previous_state = current_state

            if len(data) >= next_status:
                print(f"[DATA] {len(data)} samples collected", flush=True)
                next_status += 100

            await asyncio.sleep(SAMPLE_TIME)

    except KeyboardInterrupt:
        print("\n[COLLECT] Interrupted.")
    finally:
        stop_event.set()
        if server_started:
            try:
                await server.async_setValues(DEVICE_ID, 3, HR_COMMAND, [0])
            finally:
                await server.shutdown()
        save_dataset(data)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass