
import time
import asyncio

import gymnasium as gym
from gymnasium import spaces
import numpy as np


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
# Conveyor Environment
# ============================================================

class ConveyorEnv(gym.Env):

    metadata = {
        "render_modes": []
    }

    def __init__(
        self,
        read_hr,
        write_hr,
        event_loop,
        step_time=0.1,
        reset_wait=0.3,
        max_steps=500,
        target_round_trips=3,
        stop_penalty=0.05,
    ):

        super().__init__()

        self.read_hr_async = read_hr
        self.write_hr_async = write_hr
        self.event_loop = event_loop

        self.step_time = step_time
        self.reset_wait = reset_wait
        self.max_steps = max_steps
        self.target_round_trips = target_round_trips

        # STOP 행동에 대한 추가 페널티
        self.stop_penalty = stop_penalty

        # Action
        # 0 = STOP
        # 1 = LEFT
        # 2 = RIGHT
        self.action_space = spaces.Discrete(3)

        # Observation
        # [Sensor01, Sensor02, LastSensor]
        self.observation_space = spaces.MultiDiscrete(
            [2, 2, 3]
        )

        self.sensor01 = 0
        self.sensor02 = 0
        self.workpiece_lost = False

        self.last_sensor = 0

        self.prev_sensor01 = 0
        self.prev_sensor02 = 0

        self.step_count = 0
        self.round_trip_count = 0

        print(
            "[GYM] ConveyorEnv 생성 완료"
            f" | STOP Penalty={self.stop_penalty}",
            flush=True,
        )

    # ========================================================
    # Async -> Sync
    # ========================================================

    def _async_call(self, coroutine):

        future = asyncio.run_coroutine_threadsafe(
            coroutine,
            self.event_loop,
        )

        return future.result(timeout=5.0)

    # ========================================================
    # HR Read
    # ========================================================

    def _read_hr(self, address):

        return self._async_call(
            self.read_hr_async(address)
        )

    # ========================================================
    # HR Write
    # ========================================================

    def _write_hr(self, address, value):

        return self._async_call(
            self.write_hr_async(
                address,
                value,
            )
        )

    # ========================================================
    # HR0 Decode
    # ========================================================

    def _decode_sensor_word(self, sensor_word):

        self.sensor01 = (
            sensor_word >> BIT_SENSOR01
        ) & 1

        self.sensor02 = (
            sensor_word >> BIT_SENSOR02
        ) & 1

        self.workpiece_lost = bool(
            (
                sensor_word >> BIT_WORKPIECE_LOST
            ) & 1
        )

    # ========================================================
    # Action -> HR10
    # ========================================================

    def _set_action(self, action):

        if action == 0:
            command = 0

        elif action == 1:
            command = 1 << BIT_LEFT

        elif action == 2:
            command = 1 << BIT_RIGHT

        else:
            command = 0

        self._write_hr(
            HR_COMMAND,
            command,
        )

    # ========================================================
    # Unity Reset
    # ========================================================

    def _reset_unity(self):

        # STOP
        self._write_hr(
            HR_COMMAND,
            0,
        )

        time.sleep(0.05)

        # RESET ON
        self._write_hr(
            HR_COMMAND,
            1 << BIT_RESET,
        )

        time.sleep(0.1)

        # RESET OFF
        self._write_hr(
            HR_COMMAND,
            0,
        )

    # ========================================================
    # Reset
    # ========================================================

    def reset(self, seed=None, options=None):

        super().reset(seed=seed)

        self._reset_unity()

        time.sleep(self.reset_wait)

        self.step_count = 0
        self.round_trip_count = 0

        self.last_sensor = 0

        self.prev_sensor01 = 0
        self.prev_sensor02 = 0

        self.workpiece_lost = False

        sensor_word = self._read_hr(
            HR_SENSOR
        )

        self._decode_sensor_word(sensor_word)

        if self.sensor01 == 1:
            self.last_sensor = 1

        elif self.sensor02 == 1:
            self.last_sensor = 2

        self.prev_sensor01 = self.sensor01
        self.prev_sensor02 = self.sensor02

        observation = np.array(
            [
                self.sensor01,
                self.sensor02,
                self.last_sensor,
            ],
            dtype=np.int64,
        )

        info = {
            "sensor01": self.sensor01,
            "sensor02": self.sensor02,
            "workpiece_lost": self.workpiece_lost,
            "last_sensor": self.last_sensor,
            "round_trip_count": self.round_trip_count,
            "step_count": self.step_count,
        }

        return observation, info

    # ========================================================
    # Step
    # ========================================================

    def step(self, action):

        action = int(action)

        if not self.action_space.contains(action):
            raise ValueError(
                f"잘못된 Action: {action}"
            )

        # Action -> Unity
        self._set_action(action)

        time.sleep(self.step_time)

        # HR0 Read
        sensor_word = self._read_hr(
            HR_SENSOR
        )

        self._decode_sensor_word(sensor_word)

        self.step_count += 1

        # ----------------------------------------------------
        # 기본 보상 및 STOP 페널티
        # ----------------------------------------------------

        reward = -0.01

        if action == 0:
            reward -= self.stop_penalty

        terminated = False
        truncated = False

        # ====================================================
        # Workpiece Lost
        # ====================================================

        if self.workpiece_lost:

            self._set_action(0)

            reward = -10.0
            terminated = True

            print(
                "[FAIL] Workpiece Lost "
                f"| Step={self.step_count} "
                f"| Action={action}",
                flush=True,
            )

        else:

            # ================================================
            # Sensor Rising Edge
            # ================================================

            sensor01_rising = (
                self.sensor01 == 1
                and self.prev_sensor01 == 0
            )

            sensor02_rising = (
                self.sensor02 == 1
                and self.prev_sensor02 == 0
            )

            # Sensor01 -> Sensor02
            if (
                sensor02_rising
                and self.last_sensor == 1
            ):

                reward = 1.0
                self.last_sensor = 2

            # Sensor02 -> Sensor01
            elif (
                sensor01_rising
                and self.last_sensor == 2
            ):

                reward = 1.0
                self.last_sensor = 1

                self.round_trip_count += 1

            # ================================================
            # Success
            # ================================================

            if (
                self.round_trip_count
                >= self.target_round_trips
            ):

                reward = 10.0
                terminated = True

                self._set_action(0)

                print(
                    "[SUCCESS] "
                    f"RoundTrip={self.round_trip_count} "
                    f"Step={self.step_count}",
                    flush=True,
                )

            # ================================================
            # Max Step
            # ================================================

            if (
                self.step_count >= self.max_steps
                and not terminated
            ):

                reward = -5.0
                truncated = True

                self._set_action(0)

        self.prev_sensor01 = self.sensor01
        self.prev_sensor02 = self.sensor02

        observation = np.array(
            [
                self.sensor01,
                self.sensor02,
                self.last_sensor,
            ],
            dtype=np.int64,
        )

        info = {
            "sensor01": self.sensor01,
            "sensor02": self.sensor02,
            "workpiece_lost": self.workpiece_lost,
            "last_sensor": self.last_sensor,
            "action": action,
            "round_trip_count": self.round_trip_count,
            "step_count": self.step_count,
            "success": (
                terminated
                and not self.workpiece_lost
            ),
        }

        return (
            observation,
            reward,
            terminated,
            truncated,
            info,
        )

    # ========================================================
    # Close
    # ========================================================

    def close(self):

        try:
            self._set_action(0)

        except Exception:
            pass
