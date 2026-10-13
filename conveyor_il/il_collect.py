import time
from pathlib import Path

import pandas as pd
from pymodbus.client import ModbusTcpClient


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

HR_SENSOR = 0
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
# Sampling
# ============================================================

SAMPLE_TIME = 0.05


# ============================================================
# Modbus Read
# ============================================================

def read_hr(client, address):

    result = client.read_holding_registers(
        address=address,
        count=1,
        device_id=DEVICE_ID,
    )

    if result.isError():
        raise RuntimeError(
            f"HR{address} Read Error"
        )

    return int(result.registers[0])


# ============================================================
# HR10 -> Action
# ============================================================

def decode_action(hr10):

    left = (hr10 >> BIT_LEFT) & 1
    right = (hr10 >> BIT_RIGHT) & 1

    if left == 1 and right == 0:
        return ACTION_LEFT

    if left == 0 and right == 1:
        return ACTION_RIGHT

    return ACTION_STOP


# ============================================================
# Main
# ============================================================

def main():

    print()
    print("============================================")
    print(" IL DATA COLLECTION")
    print("============================================")
    print()

    client = ModbusTcpClient(
        MODBUS_IP,
        port=MODBUS_PORT,
    )

    print(
        f"[MODBUS] Connecting "
        f"{MODBUS_IP}:{MODBUS_PORT}"
    )

    if not client.connect():

        print("[ERROR] Connection Failed")
        return

    print("[MODBUS] Connected")
    print()

    print("PLC Expert 동작을 수집합니다.")
    print("종료 및 저장 : Ctrl+C")
    print()

    # ========================================================
    # Dataset
    # ========================================================

    data = []

    # 초기에는 Sensor01에서 출발한다고 가정
    last_sensor = 1

    sample_count = 0

    previous_state = None


    try:

        while True:

            # =================================================
            # PLC Read
            # =================================================

            hr0 = read_hr(
                client,
                HR_SENSOR,
            )

            hr10 = read_hr(
                client,
                HR_COMMAND,
            )


            # =================================================
            # Sensor Decode
            # =================================================

            sensor01 = (
                hr0 >> BIT_SENSOR01
            ) & 1

            sensor02 = (
                hr0 >> BIT_SENSOR02
            ) & 1

            workpiece_lost = (
                hr0 >> BIT_WORKPIECE_LOST
            ) & 1


            # =================================================
            # LastSensor
            # =================================================

            if sensor01 == 1:
                last_sensor = 1

            elif sensor02 == 1:
                last_sensor = 2


            # =================================================
            # PLC Expert Action
            # =================================================

            action = decode_action(
                hr10
            )


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

                sample_count += 1


            # =================================================
            # Console
            # =================================================

            current_state = (
                sensor01,
                sensor02,
                last_sensor,
                action,
            )

            if current_state != previous_state:

                print(
                    f"[COLLECT] "
                    f"S1={sensor01} "
                    f"S2={sensor02} "
                    f"Last={last_sensor} "
                    f"Expert={ACTION_NAMES[action]}"
                )

                previous_state = current_state


            if sample_count > 0 and sample_count % 100 == 0:

                print(
                    f"[DATA] "
                    f"{sample_count} samples collected"
                )


            time.sleep(
                SAMPLE_TIME
            )


    except KeyboardInterrupt:

        print()
        print("[COLLECT] Collection stopped.")


    finally:

        client.close()


        # ====================================================
        # Save
        # ====================================================

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

        print(
            f"Total Samples : {len(df)}"
        )

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

            print(
                f"{ACTION_NAMES[action]:5s} : {count}"
            )


        print("--------------------------------------------")
        print()

        print(
            f"Saved : {DATASET_PATH}"
        )

        print()


# ============================================================
# Entry
# ============================================================

if __name__ == "__main__":
    main()