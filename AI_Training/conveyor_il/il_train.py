from pathlib import Path

import joblib

import importlib.util
import os
import sys

import matplotlib


# ============================================================
# Matplotlib Backend (Windows / Ubuntu / macOS)
# ============================================================
#
# - macOS   : macosx (기본 내장)
# - Windows : TkAgg
# - Ubuntu  : TkAgg (python3-tk 필요) -> 없으면 QtAgg
# - 화면이 없는 환경(SSH 등) : Agg -> 창 대신 PNG 파일로 저장
#
# ============================================================

def _select_backend():

    if sys.platform.startswith("linux") and not (
        os.environ.get("DISPLAY")
        or os.environ.get("WAYLAND_DISPLAY")
    ):
        return "Agg"

    if sys.platform == "darwin":
        return "macosx"

    if importlib.util.find_spec("tkinter") is not None:
        return "TkAgg"

    for qt in ("PyQt6", "PySide6", "PyQt5", "PySide2"):
        if importlib.util.find_spec(qt) is not None:
            return "QtAgg"

    return "Agg"


MPL_BACKEND = _select_backend()
matplotlib.use(MPL_BACKEND)
import matplotlib.pyplot as plt
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    ConfusionMatrixDisplay,
)


# ============================================================
# Path
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATASET_PATH = BASE_DIR / "il_dataset.csv"
MODEL_PATH = BASE_DIR / "conveyor_il_model.pkl"


# ============================================================
# Action
# ============================================================

ACTION_STOP = 0
ACTION_LEFT = 1
ACTION_RIGHT = 2

ACTION_NAMES = {
    ACTION_STOP: "STOP",
    ACTION_LEFT: "LEFT",
    ACTION_RIGHT: "RIGHT",
}


# ============================================================
# Training Setting
# ============================================================

VALIDATION_RATIO = 0.20
RANDOM_STATE = 42


# ============================================================
# Main
# ============================================================

def main():

    print()
    print("============================================")
    print(" IL MODEL TRAINING")
    print("============================================")
    print()


    # ========================================================
    # 1. Dataset Load
    # ========================================================

    if not DATASET_PATH.exists():

        print("[ERROR] Dataset not found.")
        print(DATASET_PATH)

        return


    df = pd.read_csv(DATASET_PATH)


    print(f"Dataset       : {DATASET_PATH}")
    print(f"Total Samples : {len(df)}")


    # ========================================================
    # 2. Dataset Check
    # ========================================================

    required_columns = [
        "Sensor01",
        "Sensor02",
        "LastSensor",
        "Action",
    ]


    for column in required_columns:

        if column not in df.columns:

            print()
            print(
                f"[ERROR] Column not found : {column}"
            )

            return


    # ========================================================
    # 3. Feature / Label
    # ========================================================

    # AI가 입력으로 사용할 데이터
    X = df[
        [
            "Sensor01",
            "Sensor02",
            "LastSensor",
        ]
    ]


    # PLC Expert가 내린 정답
    y = df["Action"]


    # ========================================================
    # 4. Action Distribution
    # ========================================================

    print()
    print("============================================")
    print(" ACTION DISTRIBUTION")
    print("============================================")
    print()


    for action in sorted(y.unique()):

        count = int(
            (y == action).sum()
        )

        name = ACTION_NAMES.get(
            action,
            str(action),
        )

        print(
            f"{name:5s} : {count}"
        )


    # ========================================================
    # 5. Train / Validation Split
    # ========================================================

    X_train, X_val, y_train, y_val = train_test_split(
        X,
        y,
        test_size=VALIDATION_RATIO,
        random_state=RANDOM_STATE,
        stratify=y,
    )


    print()
    print("============================================")
    print(" TRAIN / VALIDATION")
    print("============================================")
    print()

    total_count = len(X)
    train_count = len(X_train)
    val_count = len(X_val)

    # sklearn 은 test_size(비율)에 전체 샘플 수를 곱한 뒤 올림(ceil) 하여
    # Validation 샘플 수를 정하고, 나머지를 Train 으로 사용
    val_raw = total_count * VALIDATION_RATIO

    print(f"Total Samples      : {total_count}")
    print(f"Validation Ratio   : {VALIDATION_RATIO} (설정값)")
    print()

    print("[계산식]")
    print(
        f"Validation Samples = ceil(Total x Ratio) "
        f"= ceil({total_count} x {VALIDATION_RATIO}) "
        f"= ceil({val_raw:g}) = {val_count}"
    )
    print(
        f"Train Samples      = Total - Validation "
        f"= {total_count} - {val_count} = {train_count}"
    )
    print()

    print(
        f"Train Ratio        = Train / Total "
        f"= {train_count} / {total_count} "
        f"= {train_count / total_count * 100:.2f}%"
    )

    print(
        f"Validation Ratio   = Validation / Total "
        f"= {val_count} / {total_count} "
        f"= {val_count / total_count * 100:.2f}%"
    )


    # Action 별 Train / Validation 샘플 수 (stratify 로 비율 유지)
    print()
    print("Action별 샘플 수 (stratify)")
    print("--------------------------------------------")
    print(f"{'Action':6s} | {'Total':>6s} | {'Train':>6s} | {'Val':>6s}")
    print("--------------------------------------------")

    for action in sorted(y.unique()):

        name = ACTION_NAMES.get(action, str(action))

        print(
            f"{name:6s} | "
            f"{int((y == action).sum()):6d} | "
            f"{int((y_train == action).sum()):6d} | "
            f"{int((y_val == action).sum()):6d}"
        )

    print("--------------------------------------------")
    print(
        f"{'SUM':6s} | {total_count:6d} | "
        f"{train_count:6d} | {val_count:6d}"
    )


    # ========================================================
    # 6. Model
    # ========================================================

    model = DecisionTreeClassifier(
        max_depth=5,
        random_state=RANDOM_STATE,
    )


    # ========================================================
    # 7. Training
    # ========================================================

    print()
    print("============================================")
    print(" TRAINING")
    print("============================================")
    print()

    print("Training Start...")


    model.fit(
        X_train,
        y_train,
    )


    print("Training Complete.")


    # ========================================================
    # 8. Prediction
    # ========================================================

    train_pred = model.predict(
        X_train
    )

    val_pred = model.predict(
        X_val
    )


    # ========================================================
    # 9. Accuracy
    # ========================================================

    train_accuracy = accuracy_score(
        y_train,
        train_pred,
    )

    val_accuracy = accuracy_score(
        y_val,
        val_pred,
    )


    print()
    print("============================================")
    print(" ACCURACY")
    print("============================================")
    print()

    # Accuracy = 정답 개수 / 전체 개수
    train_correct = int(
        (train_pred == y_train.to_numpy()).sum()
    )

    val_correct = int(
        (val_pred == y_val.to_numpy()).sum()
    )

    print("[계산식] Accuracy = 예측이 정답(Expert Action)과 같은 샘플 수 / 전체 샘플 수")
    print()

    print(
        f"Train Accuracy      = {train_correct} / {train_count} "
        f"= {train_accuracy:.4f} "
        f"({train_accuracy * 100:.2f}%)"
        f"   [틀린 샘플 : {train_count - train_correct}]"
    )

    print(
        f"Validation Accuracy = {val_correct} / {val_count} "
        f"= {val_accuracy:.4f} "
        f"({val_accuracy * 100:.2f}%)"
        f"   [틀린 샘플 : {val_count - val_correct}]"
    )


    # ========================================================
    # 10. Confusion Matrix
    # ========================================================

    # 데이터에 실제 존재하는 Action만 사용
    labels = sorted(
        y.unique()
    )


    cm = confusion_matrix(
        y_val,
        val_pred,
        labels=labels,
    )


    print()
    print("============================================")
    print(" VALIDATION CONFUSION MATRIX")
    print("============================================")
    print()

    print(cm)


    # ========================================================
    # 11. Policy Test
    # ========================================================

    test_states = [

        [1, 0, 1],
        [0, 0, 1],

        [0, 1, 2],
        [0, 0, 2],

    ]


    print()
    print("============================================")
    print(" POLICY TEST")
    print("============================================")
    print()


    for state in test_states:

        state_df = pd.DataFrame(
            [state],
            columns=[
                "Sensor01",
                "Sensor02",
                "LastSensor",
            ],
        )


        prediction = model.predict(
            state_df
        )


        action = int(
            prediction[0]
        )


        action_name = ACTION_NAMES.get(
            action,
            str(action),
        )


        print(
            f"{state} -> "
            f"{action} ({action_name})"
        )


    # ========================================================
    # 12. Save Model
    # ========================================================

    joblib.dump(
        model,
        MODEL_PATH,
    )


    print()
    print("============================================")
    print(" MODEL SAVED")
    print("============================================")
    print()

    print(MODEL_PATH)


    # ========================================================
    # 13. Visualization
    # ========================================================

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(13, 5),
    )


    # --------------------------------------------------------
    # Graph 1
    # Train / Validation Accuracy
    # --------------------------------------------------------

    accuracy_names = [
        f"Train\n(n={train_count}, {train_count / total_count * 100:.0f}%)",
        f"Validation\n(n={val_count}, {val_count / total_count * 100:.0f}%)",
    ]

    accuracy_fractions = [
        f"{train_correct}/{train_count}",
        f"{val_correct}/{val_count}",
    ]


    accuracy_values = [
        train_accuracy * 100,
        val_accuracy * 100,
    ]


    bars = axes[0].bar(
        accuracy_names,
        accuracy_values,
    )


    axes[0].set_title(
        "Train vs Validation Accuracy"
    )

    axes[0].set_ylabel(
        "Accuracy (%)"
    )

    axes[0].set_ylim(
        0,
        105,
    )

    axes[0].grid(
        axis="y",
        alpha=0.3,
    )


    # Accuracy 숫자 표시
    for bar, accuracy, fraction in zip(
        bars,
        accuracy_values,
        accuracy_fractions,
    ):

        axes[0].text(
            bar.get_x()
            + bar.get_width() / 2,

            bar.get_height() + 1,

            f"{fraction} = {accuracy:.2f}%",

            ha="center",
            va="bottom",
        )


    # --------------------------------------------------------
    # Graph 2
    # Confusion Matrix
    # --------------------------------------------------------

    display_labels = [

        ACTION_NAMES.get(
            label,
            str(label),
        )

        for label in labels
    ]


    disp = ConfusionMatrixDisplay(
        confusion_matrix=cm,
        display_labels=display_labels,
    )


    disp.plot(
        ax=axes[1],
        cmap="Blues",
        values_format="d",
        colorbar=False,
    )


    axes[1].set_title(
        "Validation Confusion Matrix"
    )


    # ========================================================
    # Show
    # ========================================================

    fig.suptitle(
        "Imitation Learning - Model Evaluation",
        fontsize=16,
    )


    plt.tight_layout(
        rect=[0, 0, 1, 0.94]
    )


    if MPL_BACKEND == "Agg":

        image_path = BASE_DIR / "il_train_result.png"

        fig.savefig(
            image_path,
            dpi=120,
        )

        print()
        print("[PLOT] 그래프 창을 열 수 없어 이미지로 저장했습니다.")
        print(f"[PLOT] {image_path}")

    else:

        plt.show()


# ============================================================
# Entry
# ============================================================

if __name__ == "__main__":

    main()