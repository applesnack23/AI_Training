"""Conveyor imitation-learning controller with Unity reset handshake.

Python 3.14 / PyModbus 3.16.1 server API as used by the project.
Unity writes HR0; Python writes HR10.
"""

import asyncio
import time
from pathlib import Path

import joblib
import pandas as pd
from pymodbus.server import ModbusTcpServer
from pymodbus.simulator import DataType, SimData, SimDevice

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "conveyor_il_model.pkl"

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
BIT_RESET = 2

ACTION_STOP = 0
ACTION_LEFT = 1
ACTION_RIGHT = 2
ACTION_NAMES = {0: "STOP", 1: "LEFT", 2: "RIGHT"}

CONTROL_INTERVAL = 0.05
DEBUG_INTERVAL = 1.0
RESET_PULSE_SECONDS = 0.2
RESET_TIMEOUT_SECONDS = 5.0


def get_bit(value, bit):
    return (value >> bit) & 1


def action_to_command(action):
    if action == ACTION_LEFT:
        return 1 << BIT_LEFT
    if action == ACTION_RIGHT:
        return 1 << BIT_RIGHT
    return 0


async def read_hr(server, address):
    values = await server.async_getValues(DEVICE_ID, 3, address, count=1)
    return int(values[0])


async def write_hr(server, address, value):
    await server.async_setValues(DEVICE_ID, 3, address, [int(value)])


async def il_control(server, model):
    print("\n============================================")
    print(" IL CONTROL START")
    print("============================================\n")

    last_sensor = 1
    previous_state = None
    previous_action = None
    previous_hr0 = None
    last_debug_time = 0.0

    # normal / reset_pulse / wait_clear / reset_failed
    reset_state = "normal"
    reset_pulse_deadline = 0.0
    reset_timeout_deadline = 0.0

    try:
        while True:
            try:
                hr0 = await read_hr(server, HR_SENSOR)
                sensor01 = get_bit(hr0, BIT_SENSOR01)
                sensor02 = get_bit(hr0, BIT_SENSOR02)
                workpiece_lost = get_bit(hr0, BIT_WORKPIECE_LOST)
                now = time.monotonic()

                if hr0 != previous_hr0 or now - last_debug_time >= DEBUG_INTERVAL:
                    print(
                        f"[DEBUG] HR0={hr0} BIN={hr0:016b} "
                        f"S1={sensor01} S2={sensor02} LOST={workpiece_lost} "
                        f"RESET_STATE={reset_state}",
                        flush=True,
                    )
                    previous_hr0 = hr0
                    last_debug_time = now

                if reset_state == "normal" and workpiece_lost:
                    print("[FAIL] Workpiece Lost -> STOP + RESET", flush=True)
                    await write_hr(server, HR_COMMAND, 0)
                    await write_hr(server, HR_COMMAND, 1 << BIT_RESET)
                    reset_state = "reset_pulse"
                    reset_pulse_deadline = now + RESET_PULSE_SECONDS
                    reset_timeout_deadline = now + RESET_TIMEOUT_SECONDS
                    previous_action = ACTION_STOP
                    previous_state = None

                elif reset_state == "reset_pulse":
                    if now >= reset_pulse_deadline:
                        await write_hr(server, HR_COMMAND, 0)
                        reset_state = "wait_clear"
                        print("[RESET] Pulse released; waiting for Lost=0", flush=True)

                elif reset_state == "wait_clear":
                    # Motor must remain stopped while waiting for Unity reset.
                    if not workpiece_lost:
                        last_sensor = 1
                        previous_state = None
                        previous_action = None
                        reset_state = "normal"
                        print("[RESET] Complete -> resume AI control", flush=True)
                    elif now >= reset_timeout_deadline:
                        await write_hr(server, HR_COMMAND, 0)
                        reset_state = "reset_failed"
                        print(
                            "[RESET ERROR] Unity did not clear WorkpieceLost "
                            "within timeout. Motor remains STOP.",
                            flush=True,
                        )

                elif reset_state == "reset_failed":
                    # No repeated reset pulses: inspect Unity mapping/reset logic.
                    if not workpiece_lost:
                        last_sensor = 1
                        previous_state = None
                        previous_action = None
                        reset_state = "normal"
                        print("[RESET] Lost cleared -> resume AI control", flush=True)

                if reset_state != "normal":
                    await asyncio.sleep(CONTROL_INTERVAL)
                    continue

                if sensor01:
                    last_sensor = 1
                elif sensor02:
                    last_sensor = 2

                state = [sensor01, sensor02, last_sensor]
                state_df = pd.DataFrame(
                    [state], columns=["Sensor01", "Sensor02", "LastSensor"]
                )
                action = int(model.predict(state_df)[0])
                if action not in ACTION_NAMES:
                    raise ValueError(f"Invalid model action: {action}")

                command = action_to_command(action)
                await write_hr(server, HR_COMMAND, command)

                if state != previous_state or action != previous_action:
                    print(
                        f"[STATE] S1={sensor01} S2={sensor02} "
                        f"Last={last_sensor} -> AI={ACTION_NAMES[action]} "
                        f"HR10={command}",
                        flush=True,
                    )
                    previous_state = state.copy()
                    previous_action = action

                await asyncio.sleep(CONTROL_INTERVAL)

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"[CONTROL ERROR] {exc}", flush=True)
                try:
                    await write_hr(server, HR_COMMAND, 0)
                except Exception as stop_exc:
                    print(f"[STOP ERROR] {stop_exc}", flush=True)
                await asyncio.sleep(0.5)
    finally:
        try:
            await write_hr(server, HR_COMMAND, 0)
        except Exception as exc:
            print(f"[STOP ERROR] {exc}", flush=True)


async def main():
    print("\n============================================")
    print(" CONVEYOR IMITATION LEARNING")
    print(" MODBUS TCP SERVER + AUTO RESET")
    print("============================================\n")

    if not MODEL_PATH.exists():
        print(f"[ERROR] Model not found: {MODEL_PATH}")
        print("Run il_train.py first.")
        return

    print("[MODEL] Loading...")
    model = joblib.load(MODEL_PATH)
    print(f"[MODEL] Loaded: {MODEL_PATH}")

    device = SimDevice(
        DEVICE_ID,
        SimData(0, datatype=DataType.REGISTERS, values=[0] * 50),
    )
    server = ModbusTcpServer(
        device,
        address=(MODBUS_IP, MODBUS_PORT),
    )
    control_task = None
    server_started = False

    try:
        print(f"[MODBUS] Starting {MODBUS_IP}:{MODBUS_PORT}")
        await server.serve_forever(background=True)
        server_started = True
        print("[MODBUS] Server listening.")
        control_task = asyncio.create_task(il_control(server, model))
        await control_task
    finally:
        if control_task is not None:
            control_task.cancel()
            try:
                await control_task
            except asyncio.CancelledError:
                pass
        if server_started:
            await server.shutdown()
        print("\n============================================")
        print(" IL SERVER FINISHED")
        print("============================================")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[STOP] IL Server")