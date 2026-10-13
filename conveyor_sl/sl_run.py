import asyncio
import sys

from pathlib import Path

import joblib
import pandas as pd


# ============================================================
# Path
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

MODEL_PATH = BASE_DIR / "conveyor_sl_model.pkl"


# ============================================================
# Project Root
# ============================================================

if str(PROJECT_DIR) not in sys.path:

    sys.path.insert(
        0,
        str(PROJECT_DIR),
    )


# ============================================================
# Common Modbus Server
# ============================================================

from modbus_server import (
    start_server,
    read_hr,
    write_hr,
)


# ============================================================
# Register Map
# ============================================================

HR_SENSOR = 0
HR_COMMAND = 10


# ============================================================
# HR0 Bits
# ============================================================

BIT_SENSOR01 = 0
BIT_SENSOR02 = 1
BIT_WORKPIECE_LOST = 2


# ============================================================
# HR10 Bits
# ============================================================

BIT_LEFT = 0
BIT_RIGHT = 1
BIT_RESET = 2


# ============================================================
# Actions
# ============================================================

ACTION_STOP = 0
ACTION_LEFT = 1
ACTION_RIGHT = 2


ACTION_NAMES = {
    ACTION_STOP: "STOP",
    ACTION_LEFT: "LEFT",
    ACTION_RIGHT: "RIGHT",
}


# ============================================================
# Control
# ============================================================

CONTROL_CYCLE = 0.05


# ============================================================
# Action -> HR10
# ============================================================

def action_to_command(action):

    if action == ACTION_STOP:
        return 0

    if action == ACTION_LEFT:
        return 1 << BIT_LEFT

    if action == ACTION_RIGHT:
        return 1 << BIT_RIGHT

    return 0


# ============================================================
# SL Control Loop
# ============================================================

async def sl_control_loop(model):

    # 서버가 먼저 생성될 시간을 조금 줌
    await asyncio.sleep(0.2)

    print()
    print("============================================")
    print(" SL CONTROLLER STARTED")
    print("============================================")
    print()

    last_sensor = 1

    previous_s1 = None
    previous_s2 = None
    previous_action = None

    lost_printed = False


    while True:

        # ====================================================
        # HR0 Read
        # ====================================================

        hr0 = await read_hr(
            HR_SENSOR
        )


        # ====================================================
        # Decode
        # ====================================================

        sensor01 = (
            hr0 >> BIT_SENSOR01
        ) & 1

        sensor02 = (
            hr0 >> BIT_SENSOR02
        ) & 1

        workpiece_lost = (
            hr0 >> BIT_WORKPIECE_LOST
        ) & 1


        # ====================================================
        # Workpiece Lost
        # ====================================================

        if workpiece_lost:

            await write_hr(
                HR_COMMAND,
                0,
            )

            if not lost_printed:

                print()
                print(
                    "[FAIL] Workpiece Lost"
                )
                print()

                lost_printed = True

            previous_action = ACTION_STOP

            await asyncio.sleep(
                CONTROL_CYCLE
            )

            continue


        lost_printed = False


        # ====================================================
        # LastSensor
        # ====================================================

        if sensor01 == 1:

            last_sensor = 1

        elif sensor02 == 1:

            last_sensor = 2


        # ====================================================
        # State
        # ====================================================

        state = pd.DataFrame(
            [
                [
                    sensor01,
                    sensor02,
                    last_sensor,
                ]
            ],
            columns=[
                "Sensor01",
                "Sensor02",
                "LastSensor",
            ],
        )


        # ====================================================
        # Model Inference
        # ====================================================

        action = int(
            model.predict(
                state
            )[0]
        )


        # ====================================================
        # Action -> HR10
        # ====================================================

        command = action_to_command(
            action
        )


        # ====================================================
        # HR10 Write
        # ====================================================

        await write_hr(
            HR_COMMAND,
            command,
        )


        # ====================================================
        # Log
        # ====================================================

        if (
            sensor01 != previous_s1
            or
            sensor02 != previous_s2
            or
            action != previous_action
        ):

            print(
                f"[SL] "
                f"S1={sensor01} "
                f"S2={sensor02} "
                f"Last={last_sensor} "
                f"-> "
                f"{ACTION_NAMES[action]} "
                f"(HR10={command})"
            )


        previous_s1 = sensor01
        previous_s2 = sensor02
        previous_action = action


        await asyncio.sleep(
            CONTROL_CYCLE
        )


# ============================================================
# Main
# ============================================================

async def main():

    print()
    print("============================================")
    print(" CONVEYOR SUPERVISED LEARNING")
    print("============================================")
    print()


    # ========================================================
    # Model Check
    # ========================================================

    if not MODEL_PATH.exists():

        print(
            "[ERROR] Model file not found:"
        )

        print(
            MODEL_PATH
        )

        print()
        print(
            "Run sl_train.py first."
        )

        return


    # ========================================================
    # Model Load
    # ========================================================

    print(
        "[SL] Loading model..."
    )

    model = joblib.load(
        MODEL_PATH
    )

    print(
        "[SL] Model Loaded"
    )

    print(
        f"[SL] {MODEL_PATH}"
    )


    # ========================================================
    # Start Tasks
    # ========================================================

    server_task = asyncio.create_task(
        start_server()
    )

    control_task = asyncio.create_task(
        sl_control_loop(
            model
        )
    )


    await asyncio.gather(
        server_task,
        control_task,
    )


# ============================================================
# Entry
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print()
        print("============================================")
        print(" PROGRAM STOPPED")
        print("============================================")
        print()

    except Exception as e:

        print()
        print("============================================")
        print(" ERROR")
        print("============================================")
        print()

        print(
            type(e).__name__,
            ":",
            e,
        )

        print()