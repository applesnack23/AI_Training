from pathlib import Path

import torch
from ultralytics import YOLO


BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "yolo11n.pt"

DATA_PATH = BASE_DIR / "data.yaml"


# ============================================================
# Device (Windows / Ubuntu / macOS)
# ============================================================
#
# - NVIDIA GPU (Windows / Ubuntu) : 0 (CUDA)
# - Apple Silicon Mac             : "mps"
# - 그 외                          : "cpu"
#
# ============================================================

def select_device():

    if torch.cuda.is_available():
        return 0

    mps = getattr(torch.backends, "mps", None)

    if mps is not None and mps.is_available():
        return "mps"

    return "cpu"


def main():

    print()
    print("==============================")
    print(" BOX OBJECT DETECTION TRAINING")
    print("==============================")
    print()

    device = select_device()

    print(f"[DEVICE] {device}")
    print()

    # 사전학습 YOLO 모델
    model = YOLO(str(MODEL_PATH))

    model.train(
        data=str(DATA_PATH),

        epochs=50,

        imgsz=640,

        batch=16,

        project=str(
            BASE_DIR / "runs"
        ),

        name="box_train",

        device=device,

        save_period=5,
    )


if __name__ == "__main__":
    main()