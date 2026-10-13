import asyncio
import sys
import threading
import time
from pathlib import Path

from stable_baselines3 import A2C
from stable_baselines3.common.monitor import Monitor


# ============================================================
# Path
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

MODEL_PATH = BASE_DIR / "a2c_conveyor_20k"
LOG_DIR = BASE_DIR / "a2c_logs"

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# Import Project Module
# ============================================================

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_DIR)
    )


from modbus_server import (
    start_server,
    read_hr,
    write_hr,
)

from conveyor_env import ConveyorEnv


# ============================================================
# Modbus Event Loop
# ============================================================

event_loop = None

loop_ready = threading.Event()


def modbus_thread():

    global event_loop

    # 새로운 asyncio Event Loop 생성
    event_loop = asyncio.new_event_loop()

    asyncio.set_event_loop(
        event_loop
    )

    # Event Loop 준비 완료
    loop_ready.set()

    try:

        # Modbus TCP Server 실행
        event_loop.run_until_complete(
            start_server()
        )

    except Exception as e:

        print(
            "[MODBUS THREAD ERROR]",
            e
        )


# ============================================================
# Main
# ============================================================

def main():

    print()
    print("========================================")
    print(" A2C Conveyor Training")
    print("========================================")
    print()


    # --------------------------------------------------------
    # Modbus Server Thread
    # --------------------------------------------------------

    server_thread = threading.Thread(
        target=modbus_thread,
        daemon=True,
    )

    server_thread.start()


    # Event Loop 생성 대기
    loop_ready.wait()


    # Unity Modbus 연결 대기
    time.sleep(1.0)


    # --------------------------------------------------------
    # Conveyor Environment
    # --------------------------------------------------------

    env = ConveyorEnv(

        read_hr=read_hr,

        write_hr=write_hr,

        event_loop=event_loop,

        # A2C Action 주기
        step_time=0.1,

        # Reset 후 Unity 안정화 시간
        reset_wait=0.3,

        # Episode 최대 Step
        max_steps=500,

        # 3회 왕복 성공
        target_round_trips=3,
    )


    # --------------------------------------------------------
    # Monitor
    #
    # Episode Reward / Episode Length 기록
    # --------------------------------------------------------

    env_monitor = Monitor(
        env
    )


    # ========================================================
    # A2C
    # ========================================================

    model = A2C(

        # ----------------------------------------------------
        # Policy
        # ----------------------------------------------------

        policy="MlpPolicy",


        # ----------------------------------------------------
        # Environment
        # ----------------------------------------------------

        env=env_monitor,


        # ----------------------------------------------------
        # Console Log
        # ----------------------------------------------------

        verbose=1,


        # ----------------------------------------------------
        # Rollout
        #
        # 몇 Step의 경험을 수집한 후 학습할지
        # ----------------------------------------------------

        n_steps=5,


        # ----------------------------------------------------
        # Discount Factor
        # ----------------------------------------------------

        gamma=0.99,


        # ----------------------------------------------------
        # Learning Rate
        # ----------------------------------------------------

        learning_rate=0.0007,


        # ----------------------------------------------------
        # Advantage 계산
        # ----------------------------------------------------

        gae_lambda=1.0,


        # ----------------------------------------------------
        # Entropy
        #
        # 탐색을 위한 Entropy 계수
        # ----------------------------------------------------

        ent_coef=0.0,


        # ----------------------------------------------------
        # Value Function
        # ----------------------------------------------------

        vf_coef=0.5,


        # ----------------------------------------------------
        # TensorBoard Log
        # ----------------------------------------------------

        tensorboard_log=str(
            LOG_DIR
        ),


        # ----------------------------------------------------
        # Device
        # ----------------------------------------------------

        device="cpu",
    )


    # ========================================================
    # Training
    # ========================================================

    print()
    print("[A2C] Training Start")
    print()


    model.learn(

        total_timesteps=20000,

        progress_bar=False,

        tb_log_name="A2C_Conveyor",
    )


    # ========================================================
    # Save Model
    # ========================================================

    model.save(
        str(MODEL_PATH)
    )


    print()
    print(
        "[A2C] Model Saved:",
        MODEL_PATH
    )


    # ========================================================
    # Close
    # ========================================================

    env_monitor.close()


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":

    main()