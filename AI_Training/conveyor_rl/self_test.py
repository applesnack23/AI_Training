"""
self_test.py — 트윈 없이 1 ~ 2 분 만에 학습 코드 전체를 실제로 돌려 보고 검사

  python conveyor_rl\\self_test.py

  하는 일
    · twin_sim.py 와 같은 컨베이어 계산을 프로그램 안에서 돌림 (Modbus · 트윈 필요 없음)
    · 진짜 conveyor_env.py (계속 왕복 모드) + PPO 8 × 8 로 1,024 걸음 학습
    · train_logger.py · time/fps 빼기 · weights_to_tb.py 가 제대로 동작하는지 자동 검사
  결과는 conveyor_rl\\_selftest 폴더에만 생깁니다 (logs 폴더는 건드리지 않음). 확인 뒤 지워도 됩니다.
"""
import asyncio
import csv
import shutil
import subprocess
import sys
import threading
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
OUT = BASE / "_selftest"
shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir()

# ---------------------------------------------------------------- time/fps 빼기 (ppo_train*.py 에 넣은 것과 같은 코드)
from stable_baselines3.common import logger as _sb3_logger
_orig_record = _sb3_logger.Logger.record
def _record_no_fps(self, key, value, exclude=None):
    if key == "time/fps":
        exclude = ("tensorboard",)
    return _orig_record(self, key, value, exclude)
_sb3_logger.Logger.record = _record_no_fps

from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from conveyor_env import ConveyorEnv
from train_logger import TrainLogger

# ---------------------------------------------------------------- 가짜 트윈 (twin_sim.py 와 같은 계산)
SPEED, A_POS, B_POS, SEE, LOST_L, LOST_R, START = 60.0, 9, 140, 20, -22, 170, 9
HR = {0: 0, 10: 0}
box = {"x": START, "lost": 0}

def sim(dt):
    cmd = HR[10]
    if not box["lost"]:
        if cmd & 2: box["x"] += SPEED * dt
        elif cmd & 1: box["x"] -= SPEED * dt
        if box["x"] < LOST_L or box["x"] > LOST_R: box["lost"] = 1
    HR[0] = 4 if box["lost"] else int(abs(box["x"] - A_POS) <= SEE) | (int(abs(box["x"] - B_POS) <= SEE) << 1)

async def read_hr(addr):
    if addr == 0:
        for _ in range(5): sim(0.02)          # 한 걸음(0.1 초) 만큼 트윈을 진행
    return HR[addr]

async def write_hr(addr, val):
    HR[addr] = val
    if addr == 10 and val & 4:
        box["x"], box["lost"] = START, 0; sim(0)

loop = asyncio.new_event_loop()
threading.Thread(target=loop.run_forever, daemon=True).start()

# ---------------------------------------------------------------- 학습
env = Monitor(ConveyorEnv(read_hr=read_hr, write_hr=write_hr, event_loop=loop,
                          step_time=0.0, reset_wait=0.0, max_steps=500, target_round_trips=None))
model = PPO("MlpPolicy", env, policy_kwargs=dict(net_arch=dict(pi=[8, 8], vf=[8, 8])),
            n_steps=256, batch_size=64, gamma=0.99, learning_rate=0.0003, verbose=0,
            tensorboard_log=str(OUT / "logs"), device="cpu", seed=0)
model.learn(total_timesteps=1024, tb_log_name="SELFTEST", callback=TrainLogger(out_dir=OUT / "trainlog"))
model.save(str(OUT / "selftest_model"))

# ---------------------------------------------------------------- 검사
ok = True
def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(f"  [{'통과' if cond else '실패'}] {name}" + (f"  — {detail}" if detail else ""))

print("\n========== 자동 검사 ==========")
tl = OUT / "trainlog"
rows = list(csv.reader(open(tl / "steps.csv", encoding="utf-8-sig")))
check("steps.csv 걸음 기록", len(rows) - 1 == 1024, f"{len(rows) - 1} 줄")
txt = (tl / "updates.txt").read_text(encoding="utf-8")
check("updates.txt 고치기 요약 4 번", txt.count("[고치기 ") == 4)
check("updates.jsonl", sum(1 for _ in open(tl / "updates.jsonl", encoding="utf-8")) == 5)

from tensorboard.backend.event_processing import event_accumulator as ea
run = next((OUT / "logs").iterdir())
acc = ea.EventAccumulator(str(run), size_guidance={ea.SCALARS: 0, ea.HISTOGRAMS: 0, ea.TENSORS: 0}); acc.Reload()
tags = acc.Tags()
sc = set(tags.get("scalars", []))
check("TensorBoard 가중치 기록 (w_L1 · w_L2 · w_OUT)", {"w_L1/n6/A_1", "w_L2/n0/from_L1n3", "w_OUT/RIGHT/bias"} <= sc,
      f"가중치 · 편향 {sum(t.startswith('w_') for t in sc)} 개 (163 이어야 함)")
check("TensorBoard 행동 확률 (12 상태 × 3)", sum(t.startswith("prob/") for t in sc) == 36)
check("TensorBoard 층별 분포 (HISTOGRAMS)", len(tags.get("histograms", [])) == 3)
try:
    has_layout = bool(acc.PluginTagToContent("custom_scalars"))
except KeyError:
    has_layout = False
check("TensorBoard 뉴런별 배치 (CUSTOM SCALARS)", has_layout)
check("TensorBoard 점수 기록 (ep_rew_mean)", "rollout/ep_rew_mean" in sc)
check("time/fps 가 TensorBoard 에 없음", "time/fps" not in sc)

r = subprocess.run([sys.executable, str(BASE / "weights_to_tb.py"), str(tl), str(OUT / "converted")], capture_output=True, text=True)
check("weights_to_tb.py 변환", r.returncode == 0 and any((OUT / "converted").iterdir()), (r.stderr or "").strip()[-200:])

print("\n  최종:", "모두 통과" if ok else "실패한 항목이 있습니다 — 이 화면을 보내 주세요")
print(f"  결과 폴더: {OUT}  (tensorboard --logdir {OUT} 로 직접 볼 수도 있음)")
