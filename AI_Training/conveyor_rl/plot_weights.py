"""
plot_weights.py — weights_history.json 으로 「가중치가 학습 중 어떻게 바뀌었나」 그림 만들기

  python plot_weights.py                       (같은 폴더의 weights_history.json)
  python plot_weights.py weights_history.json

  만드는 그림
    weights_1_all.png      163 개 숫자 전체가 바뀌는 모습 (층별 3 칸)
    weights_2_layer1.png   1 층 길목 56 개를 표(열 지도)로 — 처음 / 중간 / 마지막
    weights_3_prob.png     자주 나오는 6 상태에서 행동 확률이 바뀌는 모습
"""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = ["Malgun Gothic", "AppleGothic", "Noto Sans CJK KR", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("weights_history.json")
D = json.loads(src.read_text())
H, LAB, ACT = D["history"], D["labels"], D["actions"]
steps = np.array([h["step"] for h in H])
out = src.parent


def arr(k, key):
    return np.array([np.array(h["layers"][k][key]) for h in H])     # (기록 수, ...)


def forward(layers, o):
    x = np.concatenate([np.eye(n)[v] for v, n in zip(o, (2, 2, 3))])
    for k, L in enumerate(layers):
        x = np.array(L["W"]) @ x + np.array(L["b"])
        if k < len(layers) - 1:
            x = np.tanh(x)
    e = np.exp(x - x.max())
    return e / e.sum()


# ---------- 1) 163 개 전체 ----------
fig, ax = plt.subplots(1, 3, figsize=(16, 5), sharex=True)
names = ["입력 → 1 층 (56 + 편향 8)", "1 층 → 2 층 (64 + 편향 8)", "2 층 → 행동 (24 + 편향 3)"]
for k in range(3):
    W, b = arr(k, "W"), arr(k, "b")
    W2 = W.reshape(len(H), -1)
    fin = np.abs(W2[-1])
    top = set(np.argsort(fin)[-4:])
    for j in range(W2.shape[1]):
        ax[k].plot(steps, W2[:, j], lw=2 if j in top else 0.7, alpha=0.95 if j in top else 0.35,
                   color=None if j in top else "#888")
        if j in top:
            n, i = divmod(j, W.shape[2])
            src_name = LAB[i] if k == 0 else f"{i}번"
            dst = ACT[n] if k == 2 else f"{n}번"
            ax[k].annotate(f"{src_name}→{dst}", (steps[-1], W2[-1, j]), fontsize=9, xytext=(4, 0), textcoords="offset points")
    for j in range(b.shape[1]):
        ax[k].plot(steps, b[:, j], lw=0.8, ls="--", color="#c58b00", alpha=0.6)
    ax[k].axhline(0, color="k", lw=0.6)
    ax[k].set_title(names[k]); ax[k].set_xlabel("학습 걸음"); ax[k].grid(alpha=0.3)
ax[0].set_ylabel("가중치 값")
fig.suptitle("학습 중 가중치 163 개가 바뀌는 모습 (굵은 선 = 마지막에 가장 큰 4 개, 노란 점선 = 편향)")
fig.tight_layout(); fig.savefig(out / "weights_1_all.png", dpi=150); plt.close(fig)

# ---------- 2) 1 층 길목 56 개 열 지도 ----------
W1 = arr(0, "W")
idx = [0, len(H) // 2, len(H) - 1]
vmax = np.abs(W1).max()
fig, ax = plt.subplots(1, 3, figsize=(15, 4.8))
for a, t in zip(ax, idx):
    im = a.imshow(W1[t], cmap="bwr", vmin=-vmax, vmax=vmax)
    a.set_xticks(range(7)); a.set_xticklabels(LAB, rotation=45, ha="right")
    a.set_yticks(range(8)); a.set_yticklabels([f"{n}번 뉴런" for n in range(8)])
    a.set_title(f"step {steps[t]}")
    for n in range(8):
        for i in range(7):
            a.text(i, n, f"{W1[t, n, i]:+.2f}", ha="center", va="center", fontsize=8)
fig.colorbar(im, ax=ax, shrink=0.8, label="가중치 (빨강 +, 파랑 −)")
fig.suptitle("1 층 길목 56 개 — 처음 / 중간 / 마지막")
fig.savefig(out / "weights_2_layer1.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# ---------- 3) 행동 확률 ----------
STATES = [((1, 0, 0), "시작 · A 위"), ((1, 0, 1), "A 위 · B 로 갈 차례"), ((0, 0, 1), "A → B 가는 중"),
          ((0, 1, 0), "시작 · B 위"), ((0, 1, 2), "B 위 · A 로 갈 차례"), ((0, 0, 2), "B → A 가는 중")]
fig, ax = plt.subplots(2, 3, figsize=(15, 7.5), sharex=True, sharey=True)
for a, (o, name) in zip(ax.ravel(), STATES):
    P = np.array([forward(h["layers"], o) for h in H])
    for k, c in zip(range(3), ["#888", "#0b57d0", "#cf222e"]):
        a.plot(steps, P[:, k], color=c, lw=2, label=ACT[k])
    a.set_title(f"A={o[0]} B={o[1]} LAST={o[2]} — {name}"); a.set_ylim(0, 1); a.grid(alpha=0.3)
ax[0, 0].legend(); ax[1, 1].set_xlabel("학습 걸음"); ax[0, 0].set_ylabel("행동 확률"); ax[1, 0].set_ylabel("행동 확률")
fig.suptitle("가중치가 바뀌면서 행동 확률이 바뀌는 모습 (처음 1/3 씩 → 정답 쪽으로)")
fig.tight_layout(); fig.savefig(out / "weights_3_prob.png", dpi=150); plt.close(fig)

print("저장:", out / "weights_1_all.png", out / "weights_2_layer1.png", out / "weights_3_prob.png")
