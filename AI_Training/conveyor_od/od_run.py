import os
import sys
from pathlib import Path
from flask import Flask, request
from ultralytics import YOLO
import cv2
import numpy as np

# ==========================================
# Path
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "runs" / "box_train" / "weights" / "best.pt"

# ==========================================
# Display (Windows / Ubuntu / macOS)
# ==========================================
#
# 화면이 없는 Linux(SSH 등)에서는 cv2.imshow 가 실패하므로
# 창 표시 없이 Detection Log 만 출력
#
# macOS 는 OpenCV 창을 Main Thread 에서만 열 수 있으므로
# Flask 를 threaded=False 로 실행 (요청을 Main Thread 에서 처리)
#
# ==========================================

SHOW_WINDOW = not (
    sys.platform.startswith("linux")
    and not (
        os.environ.get("DISPLAY")
        or os.environ.get("WAYLAND_DISPLAY")
    )
)

# ==========================================
# Model
# ==========================================

print()
print("==============================")
print(" BOX OBJECT DETECTION")
print("==============================")
print()

if not MODEL_PATH.exists():
    print("[ERROR] Model Not Found")
    print(MODEL_PATH)
    raise SystemExit

print("[MODEL] Loading...")

model = YOLO(str(MODEL_PATH))

print("[MODEL] Loaded")

# ==========================================
# HTTP Server
# ==========================================

app = Flask(__name__)


@app.route("/frame", methods=["POST"])
def receive_frame():

    # Unity에서 전송한 JPEG 데이터
    jpeg_data = request.data

    if not jpeg_data:
        return "NO DATA", 400

    # JPEG -> OpenCV Image
    np_data = np.frombuffer(jpeg_data, dtype=np.uint8)
    frame = cv2.imdecode(np_data, cv2.IMREAD_COLOR)

    if frame is None:
        return "DECODE ERROR", 400

    # ======================================
    # YOLO Inference
    # ======================================

    results = model.predict(
        source=frame,
        conf=0.5,
        verbose=False
    )

    result = results[0]

    # YOLO 결과 그리기
    display_frame = result.plot()

    # ======================================
    # Detection Log
    # ======================================

    for box in result.boxes:

        class_id = int(box.cls[0])
        confidence = float(box.conf[0])

        x1, y1, x2, y2 = box.xyxy[0].tolist()

        class_name = model.names[class_id]

        print(
            f"[DETECT] "
            f"{class_name} "
            f"Conf={confidence:.2f} "
            f"Box=({x1:.0f},{y1:.0f})-({x2:.0f},{y2:.0f})"
        )

    # ======================================
    # Display
    # ======================================

    if SHOW_WINDOW:

        cv2.imshow("YOLO - Unity Vision Camera", display_frame)

        # OpenCV 창 이벤트 처리
        if cv2.waitKey(1) & 0xFF == ord("q"):
            cv2.destroyAllWindows()

    return "OK", 200


# ==========================================
# Main
# ==========================================

if __name__ == "__main__":

    print()
    print("[HTTP] Server Started")
    print("[HTTP] http://127.0.0.1:8000/frame")

    if not SHOW_WINDOW:
        print("[DISPLAY] 화면이 없어 YOLO 창은 표시하지 않습니다.")
    print()

    app.run(
        host="127.0.0.1",
        port=8000,
        threaded=False
    )