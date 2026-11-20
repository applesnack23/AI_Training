"""
weights_to_tb.py — trainlog 폴더(updates.jsonl)의 가중치 기록을 TensorBoard 로 보기

  python conveyor_rl\\weights_to_tb.py conveyor_rl\\trainlog_20261119_121200 [저장 폴더]
  → conveyor_rl\\logs\\trainlog_20261119_121200_weights 에 TensorBoard 기록을 만듦
  → tensorboard --logdir conveyor_rl\\logs  →  CUSTOM SCALARS 탭

  (새로 고친 train_logger.py 로 학습하면 이 변환 없이도 학습 기록에 바로 들어갑니다)
"""
import json
import sys
from pathlib import Path

import numpy as np
from torch.utils.tensorboard import SummaryWriter

from train_logger import tb_layout, tb_write

src = Path(sys.argv[1])
jl = src / "updates.jsonl" if src.is_dir() else src
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent / "logs" / f"{jl.parent.name}_weights"
w = SummaryWriter(str(out))
w.add_custom_scalars(tb_layout())
n = 0
for line in open(jl, encoding="utf-8"):
    d = json.loads(line)
    if d["kind"] == "init":
        L, step = d["policy"], 0
    else:
        L, step = d["policy_after"], d["steps"][1]
    L = [{"W": np.array(l["W"]), "b": np.array(l["b"])} for l in L]
    tb_write(w, L, step)
    n += 1
w.close()
print(f"기록 {n} 개 → {out}")
print("tensorboard --logdir conveyor_rl\\logs  로 열고 CUSTOM SCALARS 탭을 보세요.")
