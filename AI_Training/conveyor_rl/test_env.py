import asyncio
import sys
import threading
import time

from pathlib import Path


# ============================================================
# Path
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent


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
# Modbus Thread
# ============================================================

event_loop = None
loop_ready = threading.Event()


def modbus_thread():

    global event_loop

    event_loop = asyncio.new_event_loop()

    asyncio.set_event_loop(
        event_loop
    )

    loop_ready.set()

    try:

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


thread = threading.Thread(
    target=modbus_thread,
    daemon=True,
)

thread.start()

loop_ready.wait()


print(
    "[SYSTEM] Modbus Server 시작 대기...",
    flush=True,
)

time.sleep(
    1.0
)


# ============================================================
# Environment
# ============================================================

env = ConveyorEnv(
    read_hr=read_hr,
    write_hr=write_hr,
    event_loop=event_loop,
    step_time=0.1,
    reset_wait=0.3,
    max_steps=500,
    target_round_trips=3,
)


# ============================================================
# Manual Test
# ============================================================

print()
print("========================================")
print(" Conveyor RL Environment Test")
print("========================================")
print("0 : STOP")
print("1 : LEFT")
print("2 : RIGHT")
print("r : RESET")
print("q : QUIT")
print("========================================")


try:

    observation, info = env.reset()


    print()
    print("[RESET]")

    print(
        "Observation =",
        observation,
    )

    print(
        "Info        =",
        info,
    )


    while True:

        print()

        command = input(
            "Command > "
        ).strip().lower()


        if command == "q":

            break


        if command == "r":

            observation, info = env.reset()

            print(
                "[RESET]"
            )

            print(
                "Observation =",
                observation,
            )

            print(
                "Info        =",
                info,
            )

            continue


        if command not in (
            "0",
            "1",
            "2",
        ):

            print(
                "0, 1, 2, r, q 중에서 입력하세요."
            )

            continue


        action = int(
            command
        )


        (
            observation,
            reward,
            terminated,
            truncated,
            info,
        ) = env.step(
            action
        )


        print(
            f"Action      = {action}"
        )

        print(
            f"Observation = {observation}"
        )

        print(
            f"Reward      = {reward}"
        )

        print(
            f"Terminated  = {terminated}"
        )

        print(
            f"Truncated   = {truncated}"
        )

        print(
            f"Info        = {info}"
        )


finally:

    env.close()

    print()
    print(
        "[SYSTEM] 종료"
    )