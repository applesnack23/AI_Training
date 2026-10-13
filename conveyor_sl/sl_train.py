from pathlib import Path

import joblib
import pandas as pd

from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
)


# ============================================================
# Path
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATASET_PATH = BASE_DIR / "sl_dataset.csv"

MODEL_PATH = BASE_DIR / "conveyor_sl_model.pkl"


# ============================================================
# Action
# ============================================================

ACTION_NAMES = {
    0: "STOP",
    1: "LEFT",
    2: "RIGHT",
}


# ============================================================
# Main
# ============================================================

def main():

    # ========================================================
    # Dataset Check
    # ========================================================

    if not DATASET_PATH.exists():

        print()
        print("[ERROR] Dataset not found:")
        print(DATASET_PATH)
        print()
        print("Run make_dataset.py first.")

        return


    # ========================================================
    # Dataset Load
    # ========================================================

    df = pd.read_csv(
        DATASET_PATH
    )


    # ========================================================
    # Feature
    # ========================================================

    X = df[
        [
            "Sensor01",
            "Sensor02",
            "LastSensor",
        ]
    ]


    # ========================================================
    # Label
    # ========================================================

    y = df["Label"]


    # ========================================================
    # Model
    # ========================================================

    model = DecisionTreeClassifier(
        max_depth=5,
        random_state=42,
    )


    # ========================================================
    # Training
    # ========================================================

    print()
    print("============================================")
    print(" SL TRAINING")
    print("============================================")
    print()

    print(
        f"Samples : {len(df)}"
    )

    model.fit(
        X,
        y,
    )


    # ========================================================
    # Training Result
    # ========================================================

    prediction = model.predict(
        X
    )

    accuracy = accuracy_score(
        y,
        prediction,
    )


    print()
    print(
        f"Accuracy : "
        f"{accuracy:.4f}"
    )


    print()
    print("Confusion Matrix")

    print(
        confusion_matrix(
            y,
            prediction,
        )
    )


    # ========================================================
    # Policy Test
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

        action = int(
            model.predict(
                state_df
            )[0]
        )

        print(
            f"{state} "
            f"-> "
            f"{ACTION_NAMES[action]}"
        )


    # ========================================================
    # Save
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
    print()


if __name__ == "__main__":

    main()