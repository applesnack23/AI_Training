from pathlib import Path

import joblib

import matplotlib
matplotlib.use("TkAgg")
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

    print(
        f"Train Samples      : {len(X_train)}"
    )

    print(
        f"Validation Samples : {len(X_val)}"
    )

    print(
        f"Train Ratio        : "
        f"{(1 - VALIDATION_RATIO) * 100:.0f}%"
    )

    print(
        f"Validation Ratio   : "
        f"{VALIDATION_RATIO * 100:.0f}%"
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

    print(
        f"Train Accuracy      : "
        f"{train_accuracy:.4f} "
        f"({train_accuracy * 100:.2f}%)"
    )

    print(
        f"Validation Accuracy : "
        f"{val_accuracy:.4f} "
        f"({val_accuracy * 100:.2f}%)"
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
        "Train",
        "Validation",
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
    for bar, accuracy in zip(
        bars,
        accuracy_values,
    ):

        axes[0].text(
            bar.get_x()
            + bar.get_width() / 2,

            bar.get_height() + 1,

            f"{accuracy:.2f}%",

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


    plt.show()


# ============================================================
# Entry
# ============================================================

if __name__ == "__main__":

    main()