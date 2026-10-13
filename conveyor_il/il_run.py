from pathlib import Path
import sys
import asyncio

import joblib
import pandas as pd


# ============================================================
# Path
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

MODEL_PATH = BASE_DIR / "conveyor_il_model.pkl"


# 상위 폴더의 modbus_server.py import
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


from modbus_server import (
    SimData,
    SimDevice,
    DataType,
    ModbusTcpServer,
)


# ============================================================
# Modbus Setting
# ============================================================

MODBUS_IP = "127.0.0.1"
MODBUS_PORT = 1502

# Unity -> Python
HR_SENSOR = 0

# Python -> Unity
HR_COMMAND = 10


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
BIT_RESET = 2


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


# ============================================================
# Control Setting
# ============================================================

CONTROL_INTERVAL = 0.05


# ============================================================
# Bit
# ============================================================

def get_bit(value, bit):

    return (value >> bit) & 1


# ============================================================
# Action -> HR10
# ============================================================

def action_to_command(action):

    if action == ACTION_LEFT:

        # HR10 bit0
        return 1 << BIT_LEFT

    elif action == ACTION_RIGHT:

        # HR10 bit1
        return 1 << BIT_RIGHT

    else:

        # STOP
        return 0


# ============================================================
# IL Control
# ============================================================

async def il_control(server, model):

    print()
    print("============================================")
    print(" IL CONTROL START")
    print("============================================")
    print()

    # 시작 위치는 Sensor01이라고 가정
    last_sensor = 1

    previous_state = None
    previous_action = None

    while True:

        try:

            # =================================================
            # HR0 Read
            # Unity -> Python
            # =================================================

            values = await server.async_getValues(
                3,
                HR_SENSOR,
                count=1,
            )

            hr0 = values[0]


            # =================================================
            # Decode Sensor
            # =================================================

            sensor01 = get_bit(
                hr0,
                BIT_SENSOR01,
            )

            sensor02 = get_bit(
                hr0,
                BIT_SENSOR02,
            )

            workpiece_lost = get_bit(
                hr0,
                BIT_WORKPIECE_LOST,
            )


            # =================================================
            # Workpiece Lost
            # =================================================

            if workpiece_lost:

                await server.async_setValues(
                    3,
                    HR_COMMAND,
                    [0],
                )

                if previous_action != ACTION_STOP:

                    print(
                        "[FAIL] Workpiece Lost -> STOP"
                    )

                previous_action = ACTION_STOP

                await asyncio.sleep(
                    CONTROL_INTERVAL
                )

                continue


            # =================================================
            # Last Sensor
            # =================================================

            if sensor01 == 1:

                last_sensor = 1

            elif sensor02 == 1:

                last_sensor = 2


            # =================================================
            # AI Input
            # =================================================

            state = [
                sensor01,
                sensor02,
                last_sensor,
            ]


            state_df = pd.DataFrame(
                [state],
                columns=[
                    "Sensor01",
                    "Sensor02",
                    "LastSensor",
                ],
            )


            # =================================================
            # IL Prediction
            # =================================================

            prediction = model.predict(
                state_df
            )

            action = int(
                prediction[0]
            )


            # =================================================
            # Action -> HR10
            # =================================================

            command = action_to_command(
                action
            )


            # =================================================
            # HR10 Write
            # Python -> Unity
            # =================================================

            await server.async_setValues(
                3,
                HR_COMMAND,
                [command],
            )


            # =================================================
            # Log
            # =================================================

            if (
                state != previous_state
                or action != previous_action
            ):

                print(
                    f"[STATE] "
                    f"S1={sensor01} "
                    f"S2={sensor02} "
                    f"Last={last_sensor} "
                    f"-> "
                    f"AI={ACTION_NAMES.get(action, action)} "
                    f"HR10={command}"
                )

                previous_state = state.copy()
                previous_action = action


            await asyncio.sleep(
                CONTROL_INTERVAL
            )


        except asyncio.CancelledError:

            raise


        except Exception as e:

            print(
                f"[CONTROL ERROR] {e}"
            )

            await asyncio.sleep(
                0.5
            )


# ============================================================
# Main
# ============================================================

async def main():

    print()
    print("============================================")
    print(" CONVEYOR IMITATION LEARNING")
    print(" MODBUS TCP SERVER")
    print("============================================")
    print()


    # ========================================================
    # Model Load
    # ========================================================

    if not MODEL_PATH.exists():

        print("[ERROR] IL Model not found.")
        print()
        print(MODEL_PATH)
        print()
        print("Run il_train.py first.")

        return


    print("[MODEL] Loading...")

    model = joblib.load(
        MODEL_PATH
    )

    print("[MODEL] Loaded")
    print(MODEL_PATH)


    # ========================================================
    # Modbus Data
    # ========================================================

    sim_data = SimData(
        block_type=DataType.REGISTERS,
        address=0,
        count=20,
        default_value=0,
    )


    # ========================================================
    # Modbus Device
    # ========================================================

    device = SimDevice(
        blocks=[sim_data],
    )


    # ========================================================
    # Modbus Server
    # ========================================================

    server = ModbusTcpServer(
        device=device,
        address=(
            MODBUS_IP,
            MODBUS_PORT,
        ),
    )


    print()
    print(
        f"[MODBUS] Server Starting "
        f"{MODBUS_IP}:{MODBUS_PORT}"
    )

    print()
    print(
        "[MODBUS] Waiting for Unity Client..."
    )


    # ========================================================
    # IL Control Task
    # ========================================================

    control_task = asyncio.create_task(
        il_control(
            server,
            model,
        )
    )


    try:

        # Modbus TCP Server 실행
        await server.serve_forever()


    except KeyboardInterrupt:

        print()
        print("[STOP] Ctrl+C")


    finally:

        control_task.cancel()

        try:

            await control_task

        except asyncio.CancelledError:

            pass


        print()
        print("============================================")
        print(" IL SERVER FINISHED")
        print("============================================")


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
        print("[STOP] IL Server")