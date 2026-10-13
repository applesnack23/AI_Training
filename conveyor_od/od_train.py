from pathlib import Path

from ultralytics import YOLO


BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = BASE_DIR / "yolo11n.pt"

DATA_PATH = BASE_DIR / "data.yaml"


def main():

    print()
    print("==============================")
    print(" BOX OBJECT DETECTION TRAINING")
    print("==============================")
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

        device=0,

        save_period=5,
    )


if __name__ == "__main__":
    main()