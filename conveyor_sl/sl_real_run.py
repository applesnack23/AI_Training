import time
from pathlib import Path

import joblib
import pandas as pd

from gpiozero import (
    DigitalInputDevice,
    DigitalOutputDevice,
)


# ============================================================
# Path
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "conveyor_sl_model.pkl"


# ============================================================
# GPIO Mapping
#
# BCM GPIO Number
# ============================================================

PIN_SENSOR01 = 17
PIN_SENSOR02 = 27

PIN_LEFT = 22
PIN_RIGHT = 23


# ============================================================
# Control Cycle
# ============================================================

CONTROL_CYCLE = 0.05


# ============================================================
# GPIO Input
# ============================================================

sensor01_input = DigitalInputDevice(
    PIN_SENSOR01,
    pull_up=False,
)

sensor02_input = DigitalInputDevice(
    PIN_SENSOR02,
    pull_up=False,
)


# ============================================================
# GPIO Output
# ============================================================

left_output = DigitalOutputDevice(
    PIN_LEFT,
    initial_value=False,
)

right_output = DigitalOutputDevice(
    PIN_RIGHT,
    initial_value=False,
)


# ============================================================
# Action
#
# 0 = STOP
# 1 = LEFT
# 2 = RIGHT
# ============================================================

def set_action(action):

    if action == 0:

        left_output.off()
        right_output.off()

    elif action == 1:

        left_output.on()
        right_output.off()

    elif action == 2:

        left_output.off()
        right_output.on()

    else:

        left_output.off()
        right_output.off()


# ============================================================
# Main
# ============================================================

def main():

    print()
    print("========================================")
    print(" SL Real Conveyor Control")
    print(" Raspberry Pi Zero 2 W")
    print("========================================")
    print()


    # --------------------------------------------------------
    # Model Check
    # --------------------------------------------------------

    if not MODEL_PATH.exists():

        print(
            "[ERROR] Model not found:",
            MODEL_PATH
        )

        return


    # --------------------------------------------------------
    # Load Model
    # --------------------------------------------------------

    model = joblib.load(
        MODEL_PATH
    )

    print(
        "[SL] Model Loaded:",
        MODEL_PATH
    )


    # --------------------------------------------------------
    # State
    # --------------------------------------------------------

    last_sensor = 0

    previous_action = None
    previous_sensor_state = None


    try:

        while True:

            # ------------------------------------------------
            # GPIO Input
            # ------------------------------------------------

            sensor01 = int(
                sensor01_input.value
            )

            sensor02 = int(
                sensor02_input.value
            )


            # ------------------------------------------------
            # Last Sensor
            # ------------------------------------------------

            if sensor01 == 1:

                last_sensor = 1

            elif sensor02 == 1:

                last_sensor = 2


            # ------------------------------------------------
            # Observation
            # ------------------------------------------------

            observation = pd.DataFrame(
                [[
                    sensor01,
                    sensor02,
                    last_sensor,
                ]],
                columns=[
                    "Sensor01",
                    "Sensor02",
                    "LastSensor",
                ]
            )


            # ------------------------------------------------
            # SL Prediction
            # ------------------------------------------------

            action = int(
                model.predict(
                    observation
                )[0]
            )


            # ------------------------------------------------
            # GPIO Output
            # ------------------------------------------------

            set_action(
                action
            )


            # ------------------------------------------------
            # Console Log
            # ------------------------------------------------

            sensor_state = (
                sensor01,
                sensor02,
                last_sensor,
            )


            if (
                action != previous_action
                or
                sensor_state != previous_sensor_state
            ):

                action_name = {
                    0: "STOP",
                    1: "LEFT",
                    2: "RIGHT",
                }.get(
                    action,
                    "UNKNOWN"
                )


                print(
                    f"[SL] "
                    f"S1={sensor01} "
                    f"S2={sensor02} "
                    f"Last={last_sensor} "
                    f"-> {action_name}"
                )


                previous_action = action
                previous_sensor_state = sensor_state


            time.sleep(
                CONTROL_CYCLE
            )


    except KeyboardInterrupt:

        print()
        print("[SL] Stopped")


    finally:

        # 안전 정지
        set_action(0)

        sensor01_input.close()
        sensor02_input.close()

        left_output.close()
        right_output.close()


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":

    main()