# Conveyor Digital Twin

## Architecture

Unity (Modbus TCP Client) <-> Modbus TCP <-> Controller (Modbus TCP Server)

Controller = CODESYS V3.5 PLC  or  Python (Modbus TCP Server + AI)

## System Overview

- **Unity**: Digital twin simulation environment
- **Modbus TCP**: Communication interface between Unity and the controller
- **PLC**: CODESYS V3.5 (CODESYS Control Win SL SoftPLC or a CODESYS-based PLC)
  - Ladder control (automatic reciprocation, interlock, timer/counter)
  - Operates as a Modbus TCP Server (ModbusTCP Slave Device)
- **Python**: Modbus TCP Server for AI control, or Modbus TCP Client for PLC data collection

## Communication Architecture

- Unity always operates as a Modbus TCP Client.
- The controller operates as the Modbus TCP Server. The controller is either the CODESYS PLC or Python.
- Only one Modbus TCP Server may run on the port at a time (PLC or Python, not both).
- Unity and the controller exchange data through Modbus Holding Registers.
- Do not reverse Unity's client role.

### Mode 1: PLC control

Unity (Client) -> CODESYS PLC (Server) <- Python (Client, optional)

- The PLC Ladder program controls the conveyor.
- Python may connect to the PLC as a Modbus TCP Client only to collect data (e.g. il_collect.py).
- In this mode Python must not write HR0 (sensors) and must not write HR10 (command).

### Mode 2: Python / AI control

Unity (Client) -> Python (Server)

- Python (modbus_server.py and AI modules) controls the conveyor.
- The PLC Modbus server must be stopped or use a different port.

## Register Map

| Register | Bit | Meaning | Direction |
| --- | --- | --- | --- |
| HR0 | 0 | Sensor01 | Unity -> Controller |
| HR0 | 1 | Sensor02 | Unity -> Controller |
| HR0 | 2 | WorkpieceLost | Unity -> Controller |
| HR10 | 0 | LEFT | Controller -> Unity |
| HR10 | 1 | RIGHT | Controller -> Unity |
| HR10 | 2 | RESET | Controller -> Unity |

- Unity writes HR0-HR9 and reads HR10-HR19 with FC23 (Read/Write Multiple Registers) every 20 ms.
- Default address: 127.0.0.1:1502, Unit ID 1.
- LEFT and RIGHT must never be 1 at the same time.

## CODESYS V3.5 Modbus TCP Server Settings

- Device tree: Ethernet -> ModbusTCP Slave Device.
- Port: 1502 (same as ModbusController.port in Unity).
- Unit ID: 1.
- Holding registers: 20, start address 0.
- Holding registers "Writable": ON.
  - Writable holding registers are mapped to %QW, so Unity can write HR0 and the PLC can write HR10 in the same register area.
  - Confirm the actual %QW addresses in the I/O mapping view.
- Map HR0 to the sensor word and HR10 to the command word in the PLC program.
- Without a license, CODESYS Control Win SL stops after 2 hours. Restart the runtime when it stops.

## Main Modules

### PLC

- CODESYS V3.5 project
  - Ladder program for conveyor control
  - ModbusTCP Slave Device configuration
  - Register map variables (HR0 sensors, HR10 command)

### Communication

- ModbusClient.cs
  - Modbus TCP Client communication
  - Connect to the controller's Modbus TCP Server (CODESYS PLC or Python)
  - Holding Register read/write
  - Sensor data transmission
  - Motor command reception

### Conveyor

- ConveyorController.cs
  - Conveyor movement
  - Motor control

### Sensors

- SensorTrigger.cs
  - Object detection
  - Sensor state

### UI

- SystemStatus.cs
  - Motor and sensor status

### Python AI

- modbus_server.py
  - Modbus TCP Server
  - Holding Register management
  - Data exchange with Unity

- conveyor_env.py
  - AI environment
  - Observation and action processing
  - Reward calculation

- train_ppo.py
  - PPO reinforcement learning

- train_dqn.py
  - DQN reinforcement learning

## Communication Rules

- Unity must always operate as the Modbus TCP Client.
- The controller (CODESYS PLC or Python) must operate as the Modbus TCP Server.
- Run only one Modbus TCP Server on the port at a time.
- When the PLC is the server, Python connects as a Modbus TCP Client for data collection only.
- Preserve existing Modbus register addresses.
- Preserve existing communication protocols.
- Do not change register bit assignments without approval.
- Do not modify the Client/Server architecture without approval.

## Important Rules

- Do not change unrelated scripts.
- Preserve existing public interfaces.
- Read only relevant source files.
- Avoid scanning the entire Unity project.
- Do not modify scenes or prefabs unless required.
- Do not modify existing AI training algorithms unless requested.
- Maintain compatibility with existing Python AI modules.
- Maintain compatibility with the CODESYS V3.5 PLC project (register map and Modbus settings).
