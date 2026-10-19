import asyncio
import sys
import threading
import time

from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor


# ============================================================
# Path
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

MODEL_PATH = BASE_DIR / "ppo_conveyor_20k"
LOG_DIR = BASE_DIR / "logs"


if str(PROJECT_DIR) not in sys.path:

    sys.path.insert(
        0,
        str(PROJECT_DIR),
    )


# ============================================================
# Import
# ============================================================

from modbus_server import (
    start_server,
    read_hr,
    write_hr,
)

from conveyor_env import ConveyorEnv


# ============================================================
# Log Directory
# ============================================================

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# Modbus Thread
# ============================================================

event_loop = None
loop_ready = threading.Event()


def modbus_thread():

    global event_loop

    # --------------------------------------------------------
    # Modbus 전용 AsyncIO Event Loop
    # --------------------------------------------------------

    event_loop = asyncio.new_event_loop()

    asyncio.set_event_loop(
        event_loop
    )

    # Main Thread에 Event Loop 준비 완료 알림
    loop_ready.set()


    try:

        # ----------------------------------------------------
        # Modbus TCP Server 실행
        # ----------------------------------------------------

        event_loop.run_until_complete(
            start_server()
        )


    except Exception as e:

        print(
            "[MODBUS THREAD ERROR]",
            type(e).__name__,
            ":",
            e,
            flush=True,
        )


# ============================================================
# Modbus Server Start
# ============================================================

print()
print("========================================")
print(" Conveyor RL Training")
print("========================================")
print()


thread = threading.Thread(
    target=modbus_thread,
    daemon=True,
)

thread.start()


# Event Loop 생성 대기
loop_ready.wait()


print(
    "[SYSTEM] Modbus Server 시작 대기...",
    flush=True,
)


# Unity가 Modbus Server에 연결될 시간
time.sleep(
    1.0
)


# ============================================================
# Gymnasium Environment
# ============================================================

env = ConveyorEnv(

    read_hr=read_hr,

    write_hr=write_hr,

    event_loop=event_loop,

    # PPO Action 주기
    step_time=0.1,

    # Reset 후 Unity 안정화 시간
    reset_wait=0.3,

    # Episode 최대 Step
    max_steps=500,

    # 3회 왕복 성공
    target_round_trips=3,
)


# ============================================================
# Monitor
#
# Episode Reward / Episode Length 기록
# ============================================================

env = Monitor(
    env
)


# ============================================================
# PPO Model
# ============================================================

model = PPO(

    # --------------------------------------------------------
    # Policy
    # --------------------------------------------------------

    policy="MlpPolicy",


    # --------------------------------------------------------
    # Environment
    # --------------------------------------------------------

    env=env,


    # --------------------------------------------------------
    # Console Log
    # --------------------------------------------------------

    verbose=1,


    # --------------------------------------------------------
    # PPO Rollout
    # --------------------------------------------------------

    n_steps=256,


    # --------------------------------------------------------
    # PPO Batch
    # --------------------------------------------------------

    batch_size=64,


    # --------------------------------------------------------
    # Discount Factor
    # --------------------------------------------------------

    gamma=0.99,


    # --------------------------------------------------------
    # Learning Rate
    # --------------------------------------------------------

    learning_rate=0.0003,


    # --------------------------------------------------------
    # TensorBoard Log
    # --------------------------------------------------------

    tensorboard_log=str(
        LOG_DIR
    ),

    device="cpu",
)


# ============================================================
# Training
# ============================================================

try:

    print()
    print("========================================")
    print(" PPO Training Start")
    print("========================================")
    print()

    print("Observation")
    print("[Sensor01, Sensor02, LastSensor]")

    print()

    print("Action")
    print("0 = STOP")
    print("1 = LEFT")
    print("2 = RIGHT")

    print()

    print("Reward")
    print("Step                = -0.01")
    print("Target Sensor       = +1")
    print("Success             = +10")
    print("Workpiece Lost      = -10")
    print("Max Step            = -5")

    print()

    print("Target Round Trips  = 3")

    print("Max Episode Steps   = 500")

    print("Total Timesteps     = 20000")

    print()

    print(
        "TensorBoard Log     =",
        LOG_DIR,
    )

    print()

    print("========================================")
    print()


    # ========================================================
    # PPO Training
    # ========================================================

    model.learn(

        total_timesteps=20000,

        progress_bar=False,

        # TensorBoard Run 이름
        tb_log_name="PPO_Conveyor",
    )


    # ========================================================
    # Model Save
    # ========================================================

    model.save(
        str(MODEL_PATH)
    )


    print()
    print("========================================")
    print(" PPO Training Complete")
    print("========================================")
    print()

    print(f"Model Saved : {MODEL_PATH}.zip")

    print(f"Log Saved   : {LOG_DIR}")

    print()


# ============================================================
# Shutdown
# ============================================================

except KeyboardInterrupt:

    print()
    print(
        "[SYSTEM] Training Interrupted"
    )


finally:

    try:

        env.close()

    except Exception:

        pass


    print()
    print(
        "[SYSTEM] 종료"
    )