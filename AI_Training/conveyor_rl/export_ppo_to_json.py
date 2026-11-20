"""
[PC 에서 실행]  SB3 PPO 모델(.zip) -> 순수 파이썬용 가중치(.json) 변환

  python export_ppo_to_json.py ppo_conveyor_20k.zip ppo_policy.json

만들어진 ppo_policy.json 을 Pi 로 복사하면 ppo_run_gpio.py 가 numpy 없이 추론합니다.
"""
import json
import sys

import numpy as np
import torch.nn as nn
from gymnasium import spaces
from stable_baselines3 import PPO


def main(model_path: str, out_path: str) -> None:
    model = PPO.load(model_path, device="cpu")
    policy = model.policy

    obs_space = model.observation_space
    if isinstance(obs_space, spaces.MultiDiscrete):
        obs_kind, nvec = "multidiscrete", [int(n) for n in obs_space.nvec]
    elif isinstance(obs_space, spaces.Discrete):
        obs_kind, nvec = "discrete", [int(obs_space.n)]
    elif isinstance(obs_space, spaces.Box):
        obs_kind, nvec = "box", []
    else:
        raise SystemExit(f"지원하지 않는 관측 공간: {obs_space}")

    if not isinstance(model.action_space, spaces.Discrete):
        raise SystemExit(f"Discrete 행동 공간만 지원합니다: {model.action_space}")

    layers = []
    for m in policy.mlp_extractor.policy_net:
        if isinstance(m, nn.Linear):
            layers.append({"type": "linear",
                           "W": m.weight.detach().numpy().tolist(),
                           "b": m.bias.detach().numpy().tolist()})
        elif isinstance(m, nn.Tanh):
            layers.append({"type": "tanh"})
        elif isinstance(m, nn.ReLU):
            layers.append({"type": "relu"})
        else:
            raise SystemExit(f"지원하지 않는 레이어: {m}")
    an = policy.action_net
    layers.append({"type": "linear",
                   "W": an.weight.detach().numpy().tolist(),
                   "b": an.bias.detach().numpy().tolist()})

    # 검증용: SB3 의 정답 32개
    tests = []
    for _ in range(32):
        o = obs_space.sample()
        a, _ = model.predict(o, deterministic=True)
        tests.append({"obs": [float(v) for v in np.asarray(o).ravel()], "act": int(a)})

    with open(out_path, "w") as f:
        json.dump({"obs_kind": obs_kind, "nvec": nvec, "layers": layers, "tests": tests}, f)

    print(f"저장 완료: {out_path}")
    print(f"  관측 공간: {obs_space}  행동 공간: {model.action_space}")
    print(f"  레이어: {[l['type'] if l['type']!='linear' else f'linear{len(l['W'])}x{len(l['W'][0])}' for l in layers]}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("사용법: python export_ppo_to_json.py <model.zip> <out.json>")
    main(sys.argv[1], sys.argv[2])
