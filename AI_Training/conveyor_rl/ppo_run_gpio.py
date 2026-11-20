"""
[Pi Zero 에서 실행]  PPO 정책(순수 파이썬) 으로 컨베이어 왕복 제어 - GPIO 직접 구동

  python3 ppo_run_gpio.py              (Ctrl+C 로 종료)

필요: gpiozero (Raspberry Pi OS 기본 포함)  /  같은 폴더에 ppo_policy.json (PC 에서 export_ppo_to_json.py 로 생성)
설치할 외부 패키지 없음 (numpy 불필요, 순수 파이썬 추론)

핀 배선 (BCM / 물리)
  Sensor01 : GPIO17 / 11번
  Sensor02 : GPIO27 / 13번
  RIGHT    : GPIO22 / 15번  -> 모터 드라이버 IN1
  LEFT     : GPIO23 / 16번  -> 모터 드라이버 IN2

행동: 0=STOP, 1=LEFT, 2=RIGHT   (원래 Modbus 버전과 동일)
"""
import asyncio
import json
import math
import signal
import time
from pathlib import Path

from gpiozero import Button, DigitalOutputDevice

# ============================================================
# 설정
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
POLICY_PATH = BASE_DIR / "ppo_policy.json"

SENSOR01_PIN = 17
SENSOR02_PIN = 27
RIGHT_PIN = 22
LEFT_PIN = 23
SENSOR_ACTIVE_LOW = True      # 감지 시 LOW 센서면 True, HIGH 면 False

CONTROL_CYCLE = 0.1
TARGET_ROUND_TRIPS = 3        # 0 이면 멈추지 않고 계속 왕복 (Ctrl+C 로 끝)
INITIAL_CHECK_CYCLE = 1.0
WORKPIECE_LOST_TIMEOUT = 8.0  # 이 시간 동안 어떤 센서도 감지 안 되면 "박스 분실"로 판단

STOP, LEFT, RIGHT = 0, 1, 2
ACTION_NAME = {STOP: "STOP", LEFT: "LEFT", RIGHT: "RIGHT"}

# ============================================================
# GPIO
# ============================================================
sensor01 = Button(SENSOR01_PIN, pull_up=SENSOR_ACTIVE_LOW)
sensor02 = Button(SENSOR02_PIN, pull_up=SENSOR_ACTIVE_LOW)
out_right = DigitalOutputDevice(RIGHT_PIN)
out_left = DigitalOutputDevice(LEFT_PIN)


def set_action(action: int) -> None:
    if action == LEFT:
        out_right.off()
        out_left.on()
    elif action == RIGHT:
        out_left.off()
        out_right.on()
    else:
        out_left.off()
        out_right.off()


def read_sensors():
    return int(sensor01.is_pressed), int(sensor02.is_pressed)


# ============================================================
# 순수 파이썬 정책 (SB3 MlpPolicy 와 동일한 전처리 + 순전파, numpy 불필요)
# ============================================================
class PurePythonPolicy:
    def __init__(self, path: Path):
        with open(path) as f:
            d = json.load(f)
        self.obs_kind = d["obs_kind"]
        self.nvec = d["nvec"]
        self.layers = d["layers"]
        self.tests = d["tests"]

    def _preprocess(self, obs):
        obs = [float(v) for v in obs]
        if self.obs_kind == "multidiscrete":           # SB3 는 각 항목을 one-hot 으로 펼침
            x = []
            for v, n in zip(obs, self.nvec):
                x += [1.0 if i == int(v) else 0.0 for i in range(n)]
            return x
        if self.obs_kind == "discrete":
            return [1.0 if i == int(obs[0]) else 0.0 for i in range(self.nvec[0])]
        return obs                                      # box

    def logits(self, obs):
        x = self._preprocess(obs)
        for layer in self.layers:
            t = layer["type"]
            if t == "linear":
                x = [sum(w * xi for w, xi in zip(row, x)) + b
                     for row, b in zip(layer["W"], layer["b"])]
            elif t == "tanh":
                x = [math.tanh(v) for v in x]
            elif t == "relu":
                x = [v if v > 0 else 0.0 for v in x]
        return x

    def predict(self, obs, deterministic: bool = True):
        """SB3 의 model.predict() 와 같은 형태로 (action, None) 을 돌려준다."""
        lg = self.logits(obs)
        return lg.index(max(lg)), None

    def self_test(self) -> None:
        mismatch = sum(self.predict(t["obs"])[0] != t["act"] for t in self.tests)
        if mismatch:
            raise RuntimeError(f"파이썬 정책이 SB3 와 {mismatch}/{len(self.tests)} 건 불일치합니다")
        print(f"[RL] 정책 검증 OK ({len(self.tests)} 건 일치)")


# ============================================================
# 초기 상태 대기
# ============================================================
async def wait_for_initial_state():
    print("\n[SYSTEM] 초기 센서 상태 확인 중... (박스를 Sensor01 위치에 놓으세요)\n")
    while True:
        s1, s2 = read_sensors()
        print(f"[SENSOR] S1={s1} S2={s2}")
        if s1 == 1 and s2 == 0:
            print("\n[SYSTEM] 초기 상태 확인 완료 (Sensor01 감지)\n")
            return s1, s2
        await asyncio.sleep(INITIAL_CHECK_CYCLE)


# ============================================================
# PPO 제어 루프
# ============================================================
async def rl_control_loop(model: PurePythonPolicy):
    print("\n========================================")
    print(" PPO RL Control Start (GPIO)")
    print("========================================")
    print(f"Policy : {POLICY_PATH.name}")
    print(f"Control Cycle : {CONTROL_CYCLE}")
    print(f"Target Round Trips : {TARGET_ROUND_TRIPS}")
    print("========================================\n")

    set_action(STOP)
    prev_s1, prev_s2 = await wait_for_initial_state()

    last_sensor = 1
    prev_action = None
    prev_sensors = None
    round_trip_count = 0
    reached_sensor02 = False
    last_seen = time.monotonic()

    print("[SYSTEM] PPO 추론 시작\n")

    while True:
        s1, s2 = read_sensors()

        # ---- 박스 분실 판단 (하드웨어엔 Lost 비트가 없으므로 타임아웃으로 대체) ----
        if s1 or s2:
            last_seen = time.monotonic()
        elif time.monotonic() - last_seen > WORKPIECE_LOST_TIMEOUT:
            set_action(STOP)
            print("\n========================================")
            print(" PPO Control Failed")
            print("========================================")
            print(f"[FAIL] Workpiece Lost ({WORKPIECE_LOST_TIMEOUT}s 동안 센서 미감지)")
            print(f"[RESULT] 왕복 완료 횟수 : {round_trip_count}\n")
            return

        # ---- 상승 에지 ----
        s1_rising = s1 == 1 and prev_s1 == 0
        s2_rising = s2 == 1 and prev_s2 == 0

        if s2_rising:
            if last_sensor == 1:
                reached_sensor02 = True
                print("[EVENT] Sensor02 도착")
            last_sensor = 2
        elif s1_rising:
            if last_sensor == 2 and reached_sensor02:
                round_trip_count += 1
                reached_sensor02 = False
                print(f"[SUCCESS] 왕복 {round_trip_count}/{TARGET_ROUND_TRIPS}")
            last_sensor = 1

        prev_s1, prev_s2 = s1, s2

        if TARGET_ROUND_TRIPS > 0 and round_trip_count >= TARGET_ROUND_TRIPS:
            set_action(STOP)
            print("\n========================================")
            print(" PPO Control Complete")
            print("========================================")
            print(f"[COMPLETE] 왕복 {TARGET_ROUND_TRIPS}회 성공\n")
            return

        # ---- 관측 -> 행동 ----
        observation = [s1, s2, last_sensor]
        action, _ = model.predict(observation, deterministic=True)
        action = int(action)
        set_action(action)

        if action != prev_action or (s1, s2) != prev_sensors:
            print(f"S1={s1} S2={s2} Last={last_sensor} -> Action={action} "
                  f"({ACTION_NAME.get(action, 'UNKNOWN')}) RoundTrip={round_trip_count}")
        prev_action, prev_sensors = action, (s1, s2)

        await asyncio.sleep(CONTROL_CYCLE)


# ============================================================
# main
# ============================================================
async def main():
    print("\n[RL] 정책 로딩...")
    if not POLICY_PATH.exists():
        raise FileNotFoundError(f"정책 파일이 없습니다: {POLICY_PATH}\n"
                                f"PC 에서 export_ppo_to_json.py 로 만들어 복사하세요.")
    model = PurePythonPolicy(POLICY_PATH)
    model.self_test()
    print("[RL] PPO Model Loaded")

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    control = asyncio.create_task(rl_control_loop(model))
    waiter = asyncio.create_task(stop_event.wait())
    try:
        done, _ = await asyncio.wait({control, waiter}, return_when=asyncio.FIRST_COMPLETED)
        if control in done:
            control.result()
        else:
            print("\n[RL] Keyboard Interrupted")
            control.cancel()
    finally:
        set_action(STOP)
        print("[RL] Control Stopped")


if __name__ == "__main__":
    asyncio.run(main())
