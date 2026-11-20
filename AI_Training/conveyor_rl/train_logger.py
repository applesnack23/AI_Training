"""
train_logger.py — PPO 학습을 「걸음마다 무엇을 했나」 + 「가중치를 왜, 얼마나 고쳤나」 로 남기는 콜백

  ppo_train.py (또는 ppo_train_loop.py) 에 두 줄만 더합니다.
      from train_logger import TrainLogger
      model.learn(..., callback=TrainLogger())

  결과 폴더: conveyor_rl/trainlog_날짜_시각/
      steps.csv      걸음마다 한 줄 (엑셀로 열기)
      updates.txt    가중치를 고칠 때마다 사람이 읽는 요약
      updates.jsonl  가중치를 고칠 때마다 전체 숫자 (분석 프로그램용)

  가중치는 256 걸음(n_steps)을 모은 뒤 한꺼번에 고칩니다(64 개씩 × 10 바퀴 = 40 번).
  이 콜백은 「모으기 끝(고치기 전)」 과 「다음 모으기 시작(고친 뒤)」 의 숫자를 비교합니다.
"""
import csv
import datetime as dt
import itertools
import json
from pathlib import Path

import numpy as np
import torch.nn as nn
from stable_baselines3.common.callbacks import BaseCallback

ACT = ["STOP", "LEFT", "RIGHT"]
IN = ["A=0", "A=1", "B=0", "B=1", "LAST=0", "LAST=1", "LAST=2"]
NVEC = (2, 2, 3)
STATES = list(itertools.product(range(2), range(2), range(3)))
CLIP = 0.2


def onehot(o):
    return np.concatenate([np.eye(n)[int(v)] for v, n in zip(o, NVEC)])


def scores(layers, o):
    """행동 점수 3 개 (확률로 바꾸기 전)"""
    x = onehot(o)
    for k, L in enumerate(layers):
        x = L["W"] @ x + L["b"]
        if k < len(layers) - 1:
            x = np.tanh(x)
    return x


def softmax(s):
    e = np.exp(s - s.max())
    return e / e.sum()


# ------------------------------------------------------------------ TensorBoard 에 뉴런별로 그리기
IN_TAG = ["A_0", "A_1", "B_0", "B_1", "LAST_0", "LAST_1", "LAST_2"]


def wtag(k, n, i):
    """길목(가중치) 하나의 TensorBoard 이름. i = None 이면 편향"""
    if k == 0:
        return f"w_L1/n{n}/" + ("bias" if i is None else IN_TAG[i])
    if k == 1:
        return f"w_L2/n{n}/" + ("bias" if i is None else f"from_L1n{i}")
    return f"w_OUT/{ACT[n]}/" + ("bias" if i is None else f"from_L2n{i}")


def ptag(o, a):
    return f"prob/A{o[0]}_B{o[1]}_LAST{o[2]}/{ACT[a]}"


def tb_layout(shape=((8, 7), (8, 8), (3, 8))):
    """CUSTOM SCALARS 탭 배치 — 뉴런 하나 = 그래프 하나 (들어오는 길목 전부 + 편향)"""
    names = ["① 입력 → 1층 (뉴런별)", "② 1층 → 2층 (뉴런별)", "③ 2층 → 행동 (행동별)"]
    lay = {}
    for k, (no, ni) in enumerate(shape):
        cat = {}
        for n in range(no):
            title = f"{ACT[n]} 으로 들어오는 길목 {ni} 개 + 편향" if k == 2 else f"{k + 1}층 {n}번 뉴런으로 들어오는 길목 {ni} 개 + 편향"
            cat[title] = ["Multiline", [wtag(k, n, i) for i in range(ni)] + [wtag(k, n, None)]]
        lay[names[k]] = cat
    lay["④ 행동 확률 (12 상태)"] = {f"A={o[0]} B={o[1]} LAST={o[2]}": ["Multiline", [ptag(o, a) for a in range(3)]]
                                  for o in STATES}
    return lay


def tb_write(writer, L, step):
    """가중치 · 편향 · 12 상태 확률 · 층별 분포를 TensorBoard 에 기록"""
    for k, l in enumerate(L):
        W, b = l["W"], l["b"]
        for n in range(W.shape[0]):
            for i in range(W.shape[1]):
                writer.add_scalar(wtag(k, n, i), float(W[n, i]), step)
            writer.add_scalar(wtag(k, n, None), float(b[n]), step)
        writer.add_histogram(f"hist/{('L1', 'L2', 'OUT')[k]}_weights", W.ravel(), step)
    for o in STATES:
        p = softmax(scores(L, o))
        for a in range(3):
            writer.add_scalar(ptag(o, a), float(p[a]), step)
    writer.flush()


def wname(k, n, i):
    """가중치(길목) 이름"""
    if k == 0:
        return f"입력 {IN[i]} → 1층 {n}번"
    if k == 1:
        return f"1층 {i}번 → 2층 {n}번"
    return f"2층 {i}번 → {ACT[n]}"


def bname(k, n):
    if k == 0:
        return f"1층 {n}번 편향"
    if k == 1:
        return f"2층 {n}번 편향"
    return f"{ACT[n]} 편향"


class TrainLogger(BaseCallback):
    def __init__(self, out_dir=None, top=15, verbose=0):
        super().__init__(verbose)
        base = Path(__file__).resolve().parent
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.dir = Path(out_dir) if out_dir else base / f"trainlog_{stamp}"
        self.top = top
        self.update_no = 0
        self.episode = 0
        self.ep_step = 0
        self.step_info = []        # 이번 256 걸음의 env 정보 (on_step 에서)
        self.pending = None        # 고치기 전 기록 (다음 시작 때 비교)

    # ---------------------------------------------------------------- 숫자 꺼내기
    def _layers(self):
        p = self.model.policy
        lin = [m for m in p.mlp_extractor.policy_net if isinstance(m, nn.Linear)] + [p.action_net]
        return [{"W": l.weight.detach().cpu().numpy().astype(float).copy(),
                 "b": l.bias.detach().cpu().numpy().astype(float).copy()} for l in lin]

    def _value_layers(self):
        p = self.model.policy
        lin = [m for m in p.mlp_extractor.value_net if isinstance(m, nn.Linear)] + [p.value_net]
        return [{"W": l.weight.detach().cpu().numpy().astype(float).copy(),
                 "b": l.bias.detach().cpu().numpy().astype(float).copy()} for l in lin]

    # ---------------------------------------------------------------- 시작
    def _on_training_start(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        self.csv_f = open(self.dir / "steps.csv", "w", newline="", encoding="utf-8-sig")
        self.csv = csv.writer(self.csv_f)
        self.csv.writerow([
            "전체걸음", "고치기묶음", "에피소드", "에피소드안걸음",
            "A", "B", "LAST",
            "점수_STOP", "점수_LEFT", "점수_RIGHT",
            "확률_STOP", "확률_LEFT", "확률_RIGHT",
            "고른행동", "고른행동확률", "가치예측",
            "보상", "왕복수", "박스떨어짐", "에피소드끝", "끝난이유",
            "어드밴티지", "목표점수(return)",
            "고친뒤확률", "비율(고친뒤/고치기전)", "clip범위밖",
        ])
        self.txt = open(self.dir / "updates.txt", "w", encoding="utf-8")
        self.jsonl = open(self.dir / "updates.jsonl", "w", encoding="utf-8")
        L = self._layers()
        self.txt.write("PPO 학습 기록 — 가중치를 고칠 때마다 요약\n")
        self.txt.write(f"설정: n_steps={self.model.n_steps}, batch_size={self.model.batch_size}, "
                       f"n_epochs={self.model.n_epochs}, gamma={self.model.gamma}, gae_lambda={self.model.gae_lambda}, "
                       f"clip={CLIP}, learning_rate={self.model.learning_rate}\n\n")
        self.txt.write("[처음 가중치로 본 12 상태 행동 확률]\n" + self._state_table(L) + "\n")
        self.jsonl.write(json.dumps({"kind": "init", "step": 0, "policy": self._ser(L),
                                     "value": self._ser(self._value_layers())}, ensure_ascii=False) + "\n")
        self.txt.flush(); self.jsonl.flush()
        self.tb = None
        for fmt in getattr(self.model.logger, "output_formats", []):
            if hasattr(fmt, "writer"):                 # SB3 의 TensorBoard 기록기 (tensorboard_log 를 줬을 때)
                self.tb = fmt.writer
        if self.tb is not None:
            self.tb.add_custom_scalars(tb_layout())
            tb_write(self.tb, L, 0)
            print("[TrainLogger] TensorBoard 에도 가중치를 뉴런별로 기록합니다 (CUSTOM SCALARS 탭)", flush=True)
        print(f"[TrainLogger] 기록 폴더: {self.dir}", flush=True)

    # ---------------------------------------------------------------- 걸음마다
    def _on_rollout_start(self):
        if self.pending is not None:
            self._finish_update()
        self.step_info = []

    def _on_step(self):
        info = self.locals["infos"][0]
        done = bool(self.locals["dones"][0])
        self.ep_step += 1
        reason = ""
        if done:
            if info.get("TimeLimit.truncated", False):
                reason = "시간끝(500걸음)"
            elif info.get("workpiece_lost", False):
                reason = "박스떨어짐"
            else:
                reason = "성공"
        self.step_info.append({
            "t": int(self.num_timesteps), "ep": self.episode, "ep_step": self.ep_step,
            "reward": float(self.locals["rewards"][0]),          # 환경이 준 보상 그대로
            "round": info.get("round_trip_count", ""), "lost": int(bool(info.get("workpiece_lost", False))),
            "done": int(done), "reason": reason,
        })
        if done:
            self.episode += 1
            self.ep_step = 0
        return True

    # ---------------------------------------------------------------- 모으기 끝 (고치기 직전)
    def _on_rollout_end(self):
        rb = self.model.rollout_buffer
        n = len(self.step_info)
        obs = rb.observations[:n, 0].reshape(n, -1).astype(int)
        act = rb.actions[:n, 0].reshape(n).astype(int)
        val = rb.values[:n, 0].astype(float)
        adv = rb.advantages[:n, 0].astype(float)
        ret = rb.returns[:n, 0].astype(float)
        L = self._layers()
        sc = np.array([scores(L, o) for o in obs])
        pr = np.array([softmax(s) for s in sc])
        self.pending = {"obs": obs, "act": act, "val": val, "adv": adv, "ret": ret,
                        "sc": sc, "pr": pr, "L": L, "V": self._value_layers(),
                        "t0": self.step_info[0]["t"] if n else self.num_timesteps,
                        "t1": self.num_timesteps}

    # ---------------------------------------------------------------- 고친 뒤 (다음 모으기 시작 / 학습 끝)
    def _finish_update(self):
        P, self.pending = self.pending, None
        self.update_no += 1
        L0, L1 = P["L"], self._layers()
        V0, V1 = P["V"], self._value_layers()
        n = len(P["act"])

        # 걸음마다: 고친 뒤 확률과 비율
        new_p = np.array([softmax(scores(L1, o))[a] for o, a in zip(P["obs"], P["act"])])
        old_p = P["pr"][np.arange(n), P["act"]]
        ratio = new_p / np.maximum(old_p, 1e-12)
        for i in range(n):
            s = self.step_info[i]
            o, a = P["obs"][i], P["act"][i]
            self.csv.writerow([
                s["t"], self.update_no, s["ep"], s["ep_step"],
                o[0], o[1], o[2],
                *[f"{v:+.4f}" for v in P["sc"][i]], *[f"{v:.4f}" for v in P["pr"][i]],
                ACT[a], f"{old_p[i]:.4f}", f"{P['val'][i]:+.4f}",
                f"{s['reward']:+.3f}", s["round"], s["lost"], s["done"], s["reason"],
                f"{P['adv'][i]:+.4f}", f"{P['ret'][i]:+.4f}",
                f"{new_p[i]:.4f}", f"{ratio[i]:.4f}", int(abs(ratio[i] - 1) > CLIP),
            ])
        self.csv_f.flush()

        # 상태 · 행동별 어드밴티지 모음
        grp = {}
        for o, a, ad in zip(P["obs"], P["act"], P["adv"]):
            grp.setdefault((tuple(o), a), []).append(ad)

        # 가중치 변화
        changes = []
        for k, (a0, a1) in enumerate(zip(L0, L1)):
            d = a1["W"] - a0["W"]
            for nn_, i in itertools.product(range(d.shape[0]), range(d.shape[1])):
                changes.append((abs(d[nn_, i]), wname(k, nn_, i), a0["W"][nn_, i], a1["W"][nn_, i]))
            db = a1["b"] - a0["b"]
            for nn_ in range(len(db)):
                changes.append((abs(db[nn_]), bname(k, nn_), a0["b"][nn_], a1["b"][nn_]))
        changes.sort(key=lambda c: -c[0])
        total = sum(c[0] for c in changes)

        stats = {k.split("/", 1)[1]: float(v) for k, v in self.model.logger.name_to_value.items() if k.startswith("train/")}
        rew = [s["reward"] for s in self.step_info[:n]]
        eps = [s for s in self.step_info[:n] if s["done"]]

        # ---------- 사람이 읽는 요약
        w = self.txt.write
        w("=" * 78 + "\n")
        w(f"[고치기 {self.update_no}]  걸음 {P['t0']} ~ {P['t1']}  (이 256 걸음으로 가중치를 고침)\n")
        w(f"  모은 경험: 보상 합 {sum(rew):+.2f}, 끝난 에피소드 {len(eps)} 개"
          + (" (" + ", ".join(e['reason'] for e in eps) + ")" if eps else "") + "\n")
        acts = np.bincount(P["act"], minlength=3)
        w(f"  고른 행동 횟수: STOP {acts[0]}, LEFT {acts[1]}, RIGHT {acts[2]}\n")
        if stats:
            w("  SB3 학습 지표: " + ", ".join(f"{k}={v:.4f}" for k, v in sorted(stats.items())) + "\n")
        w(f"  고친 뒤 비율이 0.8 ~ 1.2 밖으로 나간 걸음: {int((abs(ratio - 1) > CLIP).sum())} / {n}\n")
        w("\n  [근거] 상태 · 행동별 어드밴티지 평균 (+ = 기대보다 좋았음 → 그 행동 확률 ↑)\n")
        w("     A B LAST  행동    횟수   어드밴티지 평균\n")
        for (o, a), v in sorted(grp.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            w(f"     {o[0]} {o[1]}  {o[2]}    {ACT[a]:<5} {len(v):>5}   {np.mean(v):+.3f}\n")
        w(f"\n  [결과] 가중치 변화 크기 합 {total:.4f}. 많이 바뀐 {self.top} 개:\n")
        for c in changes[:self.top]:
            w(f"     {c[1]:<22} {c[2]:+.4f} → {c[3]:+.4f}  ({c[3] - c[2]:+.4f})\n")
        w("\n  [결과] 12 상태 행동 확률 — 고치기 전 → 고친 뒤\n" + self._state_table(L0, L1, P["obs"]) + "\n")
        self.txt.flush()

        # ---------- 분석용 전체 숫자
        self.jsonl.write(json.dumps({
            "kind": "update", "update": self.update_no, "steps": [int(P["t0"]), int(P["t1"])], "train_stats": stats,
            "policy_before": self._ser(L0), "policy_after": self._ser(L1),
            "value_before": self._ser(V0), "value_after": self._ser(V1),
            "adv_by_state_action": [{"state": [int(v) for v in o], "action": ACT[a], "count": len(v), "adv_mean": float(np.mean(v))}
                                    for (o, a), v in grp.items()],
            "top_changes": [{"name": c[1], "before": float(c[2]), "after": float(c[3])} for c in changes[:self.top]],
        }, ensure_ascii=False) + "\n")
        self.jsonl.flush()
        if self.tb is not None:
            tb_write(self.tb, L1, int(P["t1"]))

    # ---------------------------------------------------------------- 끝
    def _on_training_end(self):
        if self.pending is not None:
            self._finish_update()
        self.txt.write("=" * 78 + "\n[마지막 가중치로 본 12 상태 행동 확률]\n" + self._state_table(self._layers()) + "\n")
        for f in (self.csv_f, self.txt, self.jsonl):
            f.close()
        print(f"[TrainLogger] 저장 완료: {self.dir}", flush=True)

    # ---------------------------------------------------------------- 도우미
    def _state_table(self, L0, L1=None, seen=None):
        cnt = {}
        if seen is not None:
            for o in seen:
                cnt[tuple(o)] = cnt.get(tuple(o), 0) + 1
        out = ["     A B LAST   본 횟수   STOP   LEFT  RIGHT" + ("  →  STOP   LEFT  RIGHT" if L1 else "")]
        for o in STATES:
            p0 = softmax(scores(L0, o))
            line = f"     {o[0]} {o[1]}  {o[2]}    {cnt.get(o, 0):>5}   " + " ".join(f"{v:5.2f}" for v in p0)
            if L1:
                p1 = softmax(scores(L1, o))
                line += "  →  " + " ".join(f"{v:5.2f}" for v in p1)
            out.append(line)
        return "\n".join(out) + "\n"

    @staticmethod
    def _ser(L):
        return [{"W": np.round(l["W"], 6).tolist(), "b": np.round(l["b"], 6).tolist()} for l in L]

