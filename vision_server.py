from fastapi import FastAPI, Request
import uvicorn
import cv2
import numpy as np
import threading
import time


app = FastAPI()

# 가장 최근에 Unity에서 받은 영상
latest_frame = None

# Frame 동시 접근 보호
frame_lock = threading.Lock()


# --------------------------------------------------
# 서버 동작 확인
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "status": "Vision Server Running"
    }


# --------------------------------------------------
# Unity VisionCamera 영상 수신
# --------------------------------------------------

@app.post("/frame")
async def receive_frame(request: Request):

    global latest_frame

    # Unity에서 JPEG 데이터 수신
    data = await request.body()

    if not data:
        return {
            "result": "ERROR"
        }

    # JPEG Byte → NumPy
    image_array = np.frombuffer(
        data,
        dtype=np.uint8
    )

    # NumPy → OpenCV Image
    frame = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR
    )

    if frame is None:
        return {
            "result": "ERROR"
        }

    # 최신 Frame 저장
    with frame_lock:
        latest_frame = frame

    return {
        "result": "OK"
    }


# --------------------------------------------------
# FastAPI 서버 실행
# --------------------------------------------------

def run_server():

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        access_log=False,
        log_level="warning"
    )


# --------------------------------------------------
# Main
# --------------------------------------------------

if __name__ == "__main__":

    print("--------------------------------")
    print(" Vision Monitoring System")
    print("--------------------------------")
    print("HTTP Server : 127.0.0.1:8000")
    print("Waiting for Unity VisionCamera...")
    print("ESC : Exit")
    print("--------------------------------")


    # FastAPI를 별도 Thread에서 실행
    server_thread = threading.Thread(
        target=run_server,
        daemon=True
    )

    server_thread.start()


    # ----------------------------------------------
    # OpenCV Monitoring
    # ----------------------------------------------

    while True:

        frame = None

        with frame_lock:

            if latest_frame is not None:
                frame = latest_frame.copy()


        if frame is not None:

            cv2.imshow(
                "Unity Vision Camera",
                frame
            )


        # ESC 종료
        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            break


        # CPU 과사용 방지
        time.sleep(0.01)


    cv2.destroyAllWindows()