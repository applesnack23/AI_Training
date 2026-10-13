
import asyncio
import sys
from pathlib import Path

import numpy as np
from stable_baselines3 import DQN


# ============================================================
# Path
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

MODEL_PATH = BASE_DIR / "dqn_conveyor_20k.zip"

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))


# ============================================================
# Modbus
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

BIT_SENSOR01 = 0
BIT_SENSOR02 = 1
BIT_WORKPIECE_LOST = 2

BIT_LEFT = 0
BIT_RIGHT = 1
BIT_RESET = 2


# ============================================================
# Settings
# ============================================================

# 학습 환경과 동일한 제어 주기
CONTROL_CYCLE = 0.1

# 목표 왕복 횟수
TARGET_ROUND_TRIPS = 3

# Unity Reset
RESET_PULSE_TIME = 0.1
RESET_WAIT_TIME = 0.5

# Modbus Server
SERVER_START_WAIT = 1.0

# 초기 센서 확인 주기
INITIAL_CHECK_CYCLE = 1.0


# ============================================================
# Action -> HR10
# ============================================================

async def set_action(action):

    if action == 0:
        command = 0

    elif action == 1:
        command = 1 << BIT_LEFT

    elif action == 2:
        command = 1 << BIT_RIGHT

    else:
        command = 0

    await write_hr(
        HR_COMMAND,
        command,
    )


# ============================================================
# Unity Reset
# ============================================================

async def reset_unity():

    print()
    print("[SYSTEM] Unity Reset 요청")

    # STOP
    await write_hr(
        HR_COMMAND,
        0,
    )

    await asyncio.sleep(
        RESET_PULSE_TIME
    )

    # RESET ON (HR10 Bit2)
    await write_hr(
        HR_COMMAND,
        1 << BIT_RESET,
    )

    await asyncio.sleep(
        RESET_PULSE_TIME
    )

    # RESET OFF
    await write_hr(
        HR_COMMAND,
        0,
    )

    # Unity 초기화 대기
    await asyncio.sleep(
        RESET_WAIT_TIME
    )

    print("[SYSTEM] Unity Reset 명령 완료")


# ============================================================
# Sensor Read
# ============================================================

async def read_sensors():

    sensor_word = await read_hr(
        HR_SENSOR
    )

    sensor01 = (
        sensor_word >> BIT_SENSOR01
    ) & 1

    sensor02 = (
        sensor_word >> BIT_SENSOR02
    ) & 1

    workpiece_lost = bool(
        (
            sensor_word >> BIT_WORKPIECE_LOST
        ) & 1
    )

    return (
        sensor_word,
        sensor01,
        sensor02,
        workpiece_lost,
    )


# ============================================================
# Initial State Check
# ============================================================

async def wait_for_initial_state():

    print()
    print("[SYSTEM] 초기 센서 상태 확인 중...")
    print()

    while True:

        (
            sensor_word,
            sensor01,
            sensor02,
            workpiece_lost,
        ) = await read_sensors()

        print(
            f"[SENSOR] "
            f"HR0={sensor_word} "
            f"S1={sensor01} "
            f"S2={sensor02} "
            f"Lost={int(workpiece_lost)}"
        )

        # Workpiece Lost
        if workpiece_lost:

            print(
                "[WAIT] Workpiece Lost 상태입니다. "
                "Unity Reset 상태를 확인하세요."
            )

        # 정상 시작 상태
        elif (
            sensor01 == 1
            and sensor02 == 0
        ):

            print()
            print("[SYSTEM] 초기 상태 확인 완료")
            print("[SYSTEM] Sensor01 감지 확인")
            print()

            return (
                sensor01,
                sensor02,
            )

        else:

            print(
                "[WAIT] 박스를 Sensor01 위치에 배치하세요."
            )

        await asyncio.sleep(
            INITIAL_CHECK_CYCLE
        )


# ============================================================
# DQN Control Loop
# ============================================================

async def rl_control_loop(model):

    print()
    print("========================================")
    print(" DQN RL Control Start")
    print("========================================")
    print()
    print("Model :", MODEL_PATH.name)
    print("Control Cycle :", CONTROL_CYCLE)
    print("Target Round Trips :", TARGET_ROUND_TRIPS)
    print()
    print("Action")
    print("0 = STOP")
    print("1 = LEFT")
    print("2 = RIGHT")
    print()
    print("========================================")
    print()

    # ========================================================
    # Initial Reset
    # ========================================================

    await set_action(0)

    await reset_unity()

    # ========================================================
    # Initial Sensor Check
    # ========================================================

    (
        previous_sensor01,
        previous_sensor02,
    ) = await wait_for_initial_state()

    # 초기 박스 위치는 Sensor01
    last_sensor = 1

    previous_action = None
    previous_sensor_word = None

    round_trip_count = 0
    reached_sensor02 = False

    print("[SYSTEM] DQN 추론 시작")
    print()

    # ========================================================
    # Main Loop
    # ========================================================

    while True:

        # ----------------------------------------------------
        # HR0 Read
        # ----------------------------------------------------

        (
            sensor_word,
            sensor01,
            sensor02,
            workpiece_lost,
        ) = await read_sensors()

        # ====================================================
        # Workpiece Lost
        # ====================================================

        if workpiece_lost:

            await set_action(0)

            print()
            print("========================================")
            print(" DQN Control Failed")
            print("========================================")
            print()
            print("[FAIL] Workpiece Lost")
            print(
                f"[RESULT] 왕복 완료 횟수 : "
                f"{round_trip_count}"
            )
            print()

            return

        # ====================================================
        # Rising Edge
        # ====================================================

        sensor01_rising = (
            sensor01 == 1
            and previous_sensor01 == 0
        )

        sensor02_rising = (
            sensor02 == 1
            and previous_sensor02 == 0
        )

        # ====================================================
        # Sensor02 Arrival
        # ====================================================

        if sensor02_rising:

            if last_sensor == 1:

                reached_sensor02 = True

                print(
                    "[EVENT] Sensor02 도착"
                )

            last_sensor = 2

        # ====================================================
        # Sensor01 Arrival
        # ====================================================

        elif sensor01_rising:

            if (
                last_sensor == 2
                and reached_sensor02
            ):

                round_trip_count += 1

                reached_sensor02 = False

                print(
                    f"[SUCCESS] 왕복 "
                    f"{round_trip_count}/"
                    f"{TARGET_ROUND_TRIPS}"
                )

            last_sensor = 1

        # ====================================================
        # Previous Sensor Update
        # ====================================================

        previous_sensor01 = sensor01
        previous_sensor02 = sensor02

        # ====================================================
        # Target Complete
        # ====================================================

        if (
            round_trip_count
            >= TARGET_ROUND_TRIPS
        ):

            await set_action(0)

            print()
            print("========================================")
            print(" DQN Control Complete")
            print("========================================")
            print()
            print(
                f"[COMPLETE] 왕복 "
                f"{TARGET_ROUND_TRIPS}회 성공"
            )
            print()

            return

        # ====================================================
        # Observation
        # ====================================================

        observation = np.array(
            [
                sensor01,
                sensor02,
                last_sensor,
            ],
            dtype=np.int64,
        )

        # ====================================================
        # DQN Prediction
        # ====================================================

        action, _ = model.predict(
            observation,
            deterministic=True,
        )

        action = int(action)

        # ====================================================
        # Action -> Unity
        # ====================================================

        await set_action(
            action
        )

        # ====================================================
        # Log
        # ====================================================

        if (
            action != previous_action
            or sensor_word != previous_sensor_word
        ):

            action_name = {
                0: "STOP",
                1: "LEFT",
                2: "RIGHT",
            }.get(
                action,
                "UNKNOWN",
            )

            print(
                f"S1={sensor01} "
                f"S2={sensor02} "
                f"Last={last_sensor} "
                f"-> "
                f"Action={action} "
                f"({action_name}) "
                f"RoundTrip={round_trip_count}"
            )

        previous_action = action
        previous_sensor_word = sensor_word

        await asyncio.sleep(
            CONTROL_CYCLE
        )


# ============================================================
# Main
# ============================================================

async def main():

    # ========================================================
    # Model Load
    # ========================================================

    print()
    print("[RL] DQN Model Loading...")

    if not MODEL_PATH.exists():

        raise FileNotFoundError(
            f"DQN 모델을 찾을 수 없습니다.\n"
            f"{MODEL_PATH}"
        )

    model = DQN.load(
        str(MODEL_PATH),
        device="cpu",
    )

    print("[RL] DQN Model Loaded")

    # ========================================================
    # Modbus Server Start
    # ========================================================

    print()
    print("[SYSTEM] Modbus Server 시작 중...")

    server_task = asyncio.create_task(
        start_server()
    )

    await asyncio.sleep(
        SERVER_START_WAIT
    )

    # 서버 시작 실패 확인
    if server_task.done():
        await server_task

        raise RuntimeError(
            "Modbus Server가 종료되었습니다."
        )

    # ========================================================
    # DQN Control
    # ========================================================

    try:

        await rl_control_loop(
            model
        )

    finally:

        # 종료 시 STOP
        try:
            await set_action(0)

        except Exception as e:
            print(
                "[ERROR] STOP 명령 실패:",
                e,
            )

        # Modbus Server 종료
        server_task.cancel()

        try:
            await server_task

        except asyncio.CancelledError:
            pass

        print()
        print("[RL] DQN Control Stopped")


# ============================================================
# Start
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print()
        print(
            "[RL] Keyboard Interrupted"
        )
