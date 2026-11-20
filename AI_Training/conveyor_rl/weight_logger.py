"""
weight_logger.py — PPO 학습 중 행동망 가중치(163 개)를 기록하는 콜백

  ppo_train.py 에 두 줄만 더하면 됩니다.
    from weight_logger import WeightLogger
    model.learn(..., callback=WeightLogger())

  256 걸음(한 번 모으기)마다, 가중치를 고친 직후의 숫자를 저장합니다.
  결과: conveyor_rl/weights_history.json  (그림은 plot_weights.py 로)
"""
import json
from pathlib import Path

import torch.nn as nn
from stable_baselines3.common.callbacks import BaseCallback

ACT = ["STOP", "LEFT", "RIGHT"]
LAB = ["A=0", "A=1", "B=0", "B=1", "LAST=0", "LAST=1", "LAST=2"]


class WeightLogger(BaseCallback):
    def __init__(self, path=None, watch=((0, 6, 1),), verbose=0):
        """watch: 화면에 바로 찍어 볼 가중치 (층, 뉴런, 입력) — 기본은 1 층 6 번 뉴런 ← A=1"""
        super().__init__(verbose)
        self.path = Path(path) if path else Path(__file__).with_name("weights_history.json")
        self.watch = watch
        self.hist = []

    def _layers(self):
        p = self.model.policy
        lin = [m for m in p.mlp_extractor.policy_net if isinstance(m, nn.Linear)] + [p.action_net]
        return [{"W": l.weight.detach().cpu().numpy().round(5).tolist(),
                 "b": l.bias.detach().cpu().numpy().round(5).tolist()} for l in lin]

    def _snap(self):
        L = self._layers()
        self.hist.append({"step": int(self.num_timesteps), "layers": L})
        self.path.write_text(json.dumps({"labels": LAB, "actions": ACT, "history": self.hist}))
        msg = "  ".join(f"{k + 1}층 {n}번←{LAB[i] if k == 0 else i}: {L[k]['W'][n][i]:+.3f}" for k, n, i in self.watch)
        print(f"[가중치] step={self.num_timesteps:>6}  {msg}", flush=True)

    def _on_training_start(self):      # 학습 전 (처음 아무 숫자)
        self._snap()

    def _on_rollout_start(self):       # 256 걸음 모으기 직전 = 바로 앞에서 가중치를 고친 직후
        if self.num_timesteps > 0:
            self._snap()

    def _on_training_end(self):        # 마지막 결과
        self._snap()

    def _on_step(self):
        return True
