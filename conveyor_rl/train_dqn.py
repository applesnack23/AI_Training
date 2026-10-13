import asyncio
import sys
import threading
import time
from pathlib import Path

from stable_baselines3 import DQN
from stable_baselines3.common.monitor import Monitor


# ============================================================
# Path
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

MODEL_PATH = BASE_DIR / "dqn_conveyor_20k"
LOG_DIR = BASE_DIR / "dqn_logs"

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
    print(" DQN Conveyor Training")
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

        # DQN Action 주기
        step_time=0.1,

        # Reset 후 Unity 안정화
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
    # DQN
    # ========================================================

    model = DQN(

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
        # Learning Rate
        # ----------------------------------------------------

        learning_rate=0.0001,


        # ----------------------------------------------------
        # Replay Buffer
        # ----------------------------------------------------

        buffer_size=10000,


        # ----------------------------------------------------
        # 학습 시작 전 경험 수집량
        # ----------------------------------------------------

        learning_starts=1000,


        # ----------------------------------------------------
        # Batch Size
        # ----------------------------------------------------

        batch_size=64,


        # ----------------------------------------------------
        # Discount Factor
        # ----------------------------------------------------

        gamma=0.99,


        # ----------------------------------------------------
        # 몇 Step마다 학습할지
        # ----------------------------------------------------

        train_freq=4,


        # ----------------------------------------------------
        # 한 번 학습할 때 Gradient Update 횟수
        # ----------------------------------------------------

        gradient_steps=1,


        # ----------------------------------------------------
        # Target Network Update 주기
        # ----------------------------------------------------

        target_update_interval=1000,


        # ----------------------------------------------------
        # Exploration
        # ----------------------------------------------------

        exploration_fraction=0.3,

        exploration_initial_eps=1.0,

        exploration_final_eps=0.05,


        # ----------------------------------------------------
        # TensorBoard
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
    print("[DQN] Training Start")
    print()


    model.learn(

        total_timesteps=20000,

        progress_bar=False,

        tb_log_name="DQN_Conveyor",
    )


    # ========================================================
    # Save Model
    # ========================================================

    model.save(
        str(MODEL_PATH)
    )


    print()
    print(
        "[DQN] Model Saved:",
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