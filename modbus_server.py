import asyncio

from pymodbus.server import ModbusTcpServer
from pymodbus.simulator import (
    SimData,
    SimDevice,
    DataType,
)


# ============================================================
# Configuration
# ============================================================

MODBUS_IP = "127.0.0.1"
MODBUS_PORT = 1502

DEVICE_ID = 1
HR_SIZE = 20


# ============================================================
# Register Map
# ============================================================
#
# HR0
#   bit0 = Sensor01
#   bit1 = Sensor02
#   bit2 = WorkpieceLost
#
# HR1 ~ HR9
#   Reserved
#
# HR10
#   bit0 = LEFT
#   bit1 = RIGHT
#   bit2 = RESET
#
# HR11 ~ HR19
#   Reserved
#
# ============================================================


# ============================================================
# SimData
# ============================================================

register_data = SimData(
    address=0,
    count=HR_SIZE,
    values=0,
    datatype=DataType.REGISTERS,
)


# ============================================================
# SimDevice
# ============================================================

device = SimDevice(
    id=DEVICE_ID,
    simdata=[
        register_data,
    ],
)


# ============================================================
# Server
# ============================================================

server = None


# ============================================================
# HR Read
# ============================================================

async def read_hr(address: int) -> int:

    global server

    if server is None:
        return 0

    try:

        values = await server.async_getValues(
            DEVICE_ID,
            3,              # Holding Register
            address,
            count=1,
        )

        if not values:
            return 0

        return int(values[0])

    except Exception as e:

        print(
            f"[MODBUS] HR Read Error "
            f"Address={address} "
            f"Error={e}"
        )

        return 0


# ============================================================
# HR Write
# ============================================================

async def write_hr(
    address: int,
    value: int,
):

    global server

    if server is None:
        return False

    try:

        await server.async_setValues(
            DEVICE_ID,
            3,              # Holding Register
            address,
            [int(value)],
        )

        return True

    except Exception as e:

        print(
            f"[MODBUS] HR Write Error "
            f"Address={address} "
            f"Value={value} "
            f"Error={e}"
        )

        return False


# ============================================================
# Reset
# ============================================================

async def reset_registers():

    for address in range(HR_SIZE):

        await write_hr(
            address,
            0,
        )


# ============================================================
# Server Start
# ============================================================

async def start_server():

    global server

    print()
    print("============================================")
    print(" MODBUS TCP SERVER")
    print("============================================")
    print()

    print(f"IP        : {MODBUS_IP}")
    print(f"PORT      : {MODBUS_PORT}")
    print(f"DEVICE ID : {DEVICE_ID}")

    print()
    print("Register Map")
    print("--------------------------------------------")
    print("HR0  bit0 : Sensor01")
    print("HR0  bit1 : Sensor02")
    print("HR0  bit2 : WorkpieceLost")
    print()
    print("HR10 bit0 : LEFT")
    print("HR10 bit1 : RIGHT")
    print("HR10 bit2 : RESET")
    print("--------------------------------------------")
    print()

    server = ModbusTcpServer(
        context=device,
        address=(
            MODBUS_IP,
            MODBUS_PORT,
        ),
    )

    await reset_registers()

    print(
        f"[MODBUS] Server Started "
        f"{MODBUS_IP}:{MODBUS_PORT}"
    )

    print()

    await server.serve_forever()


# ============================================================
# Standalone
# ============================================================

async def main():

    await start_server()


if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )

    except KeyboardInterrupt:

        print()
        print("[MODBUS] Server Stopped")