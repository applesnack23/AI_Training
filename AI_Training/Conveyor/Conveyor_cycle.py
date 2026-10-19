import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import modbus_server as mb


async def cycle():
    direction = 2  # RIGHT

    while True:
        sensor = await mb.read_hr(0)

        if sensor & 1:       # Sensor01
            direction = 2   # RIGHT
        elif sensor & 2:     # Sensor02
            direction = 1   # LEFT

        await mb.write_hr(10, direction)
        await asyncio.sleep(0.05)


async def main():
    await asyncio.gather(
        mb.start_server(),
        cycle()
    )


asyncio.run(main())