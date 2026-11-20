"""
Raspberry Pi Zero 용 센서 -> 방향 제어 (GPIO 직접 구동)

동작 (원래 Modbus 코드와 동일한 논리):
  Sensor01 이 감지되면 -> RIGHT
  Sensor02 가 감지되면 -> LEFT
  둘 다 아니면          -> 마지막 방향 유지

핀 배선 (BCM 번호 기준)
  Sensor01 : GPIO17 (물리 11번 핀)   - 센서 출력 -> 핀,  센서 GND -> GND
  Sensor02 : GPIO27 (물리 13번 핀)
  RIGHT    : GPIO23 (물리 16번 핀)   - 모터 드라이버 IN1 또는 LED
  LEFT     : GPIO24 (물리 18번 핀)   - 모터 드라이버 IN2 또는 LED

센서가 "감지 시 LOW" 타입(대부분의 적외선/근접 센서)이면 SENSOR_ACTIVE_LOW = True
"감지 시 HIGH" 타입이면 False 로 바꾸면 됩니다.

실행:  python3 cycle_gpio.py      (Ctrl+C 로 종료)
"""
import asyncio
import signal

from gpiozero import Button, DigitalOutputDevice

# ---- 설정 -----------------------------------------------------------------
SENSOR01_PIN = 17
SENSOR02_PIN = 27
RIGHT_PIN = 22
LEFT_PIN = 23
SENSOR_ACTIVE_LOW = True   # 감지 시 LOW 면 True, 감지 시 HIGH 면 False
POLL_SEC = 0.05            # 원래 코드의 asyncio.sleep(0.05)
# ---------------------------------------------------------------------------

LEFT, RIGHT = 1, 2

# Button 은 기본이 pull-up + active-low. active-high 센서면 pull_up=False 로.
sensor01 = Button(SENSOR01_PIN, pull_up=SENSOR_ACTIVE_LOW)
sensor02 = Button(SENSOR02_PIN, pull_up=SENSOR_ACTIVE_LOW)
out_right = DigitalOutputDevice(RIGHT_PIN)
out_left = DigitalOutputDevice(LEFT_PIN)


def apply_direction(direction: int) -> None:
    if direction == RIGHT:
        out_left.off()
        out_right.on()
    else:
        out_right.off()
        out_left.on()


async def cycle():
    direction = RIGHT
    apply_direction(direction)
    print("시작: RIGHT")

    while True:
        if sensor01.is_pressed:        # Sensor01 감지
            new_dir = RIGHT
        elif sensor02.is_pressed:      # Sensor02 감지
            new_dir = LEFT
        else:
            new_dir = direction

        if new_dir != direction:
            direction = new_dir
            apply_direction(direction)
            print("방향 ->", "RIGHT" if direction == RIGHT else "LEFT")

        await asyncio.sleep(POLL_SEC)


async def main():
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    task = asyncio.create_task(cycle())
    await stop.wait()
    task.cancel()
    out_right.off()
    out_left.off()
    print("종료")


if __name__ == "__main__":
    asyncio.run(main())
