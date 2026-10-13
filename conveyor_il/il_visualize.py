from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


# ============================================================
# Path
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "il_dataset.csv"


# ============================================================
# Action
# ============================================================

ACTION_NAMES = {
    0: "STOP",
    1: "LEFT",
    2: "RIGHT",
}


# ============================================================
# Load Dataset
# ============================================================

df = pd.read_csv(DATASET_PATH)


print()
print("============================================")
print(" IL DATASET VISUALIZATION")
print("============================================")
print()

print(f"Samples : {len(df)}")


# ============================================================
# Create One Figure
# ============================================================

fig, axes = plt.subplots(
    3,
    1,
    figsize=(13, 14),
)

fig.suptitle(
    "PLC Expert Demonstration Dataset",
    fontsize=16,
)


# ============================================================
# 1. Action Distribution
# ============================================================

action_counts = (
    df["Action"]
    .value_counts()
    .reindex([0, 1, 2], fill_value=0)
)

action_labels = [
    ACTION_NAMES[action]
    for action in action_counts.index
]


bars = axes[0].bar(
    action_labels,
    action_counts.values,
)


axes[0].set_title(
    "1. PLC Expert Action Distribution"
)

axes[0].set_xlabel(
    "Expert Action"
)

axes[0].set_ylabel(
    "Samples"
)

axes[0].grid(
    axis="y",
    alpha=0.3,
)


for bar in bars:

    height = bar.get_height()

    axes[0].text(
        bar.get_x() + bar.get_width() / 2,
        height,
        str(int(height)),
        ha="center",
        va="bottom",
    )


# ============================================================
# 2. State - Action Distribution
# ============================================================

state_counts = (
    df.groupby(
        [
            "Sensor01",
            "Sensor02",
            "LastSensor",
            "Action",
        ]
    )
    .size()
    .reset_index(
        name="Count"
    )
)


state_counts["State"] = (
    "S1="
    + state_counts["Sensor01"].astype(str)
    + " S2="
    + state_counts["Sensor02"].astype(str)
    + " Last="
    + state_counts["LastSensor"].astype(str)
    + " -> "
    + state_counts["Action"].map(ACTION_NAMES)
)


bars = axes[1].barh(
    state_counts["State"],
    state_counts["Count"],
)


axes[1].set_title(
    "2. PLC Expert State-Action Distribution"
)

axes[1].set_xlabel(
    "Samples"
)

axes[1].set_ylabel(
    "State -> Expert Action"
)

axes[1].grid(
    axis="x",
    alpha=0.3,
)


for bar in bars:

    width = bar.get_width()

    axes[1].text(
        width,
        bar.get_y() + bar.get_height() / 2,
        str(int(width)),
        va="center",
    )


# ============================================================
# 3. Action Timeline
# ============================================================

axes[2].step(
    range(len(df)),
    df["Action"],
    where="post",
)


axes[2].set_title(
    "3. PLC Expert Action Timeline"
)

axes[2].set_xlabel(
    "Sample"
)

axes[2].set_ylabel(
    "Action"
)

axes[2].set_yticks(
    [0, 1, 2],
)

axes[2].set_yticklabels(
    [
        "STOP",
        "LEFT",
        "RIGHT",
    ]
)

axes[2].grid(
    alpha=0.3,
)


# ============================================================
# Layout / Show
# ============================================================

plt.tight_layout(
    rect=[0, 0, 1, 0.97]
)

plt.show()