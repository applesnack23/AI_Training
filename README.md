# AI_Training · 컨베이어 디지털트윈 실습

컨베이어 한 대의 디지털트윈(Unity)을 PLC(CODESYS 3.5), Python, AI(지도학습·모방학습·강화학습·YOLO)로 제어하는 스마트제조 실습 자료입니다.

```
Unity (Modbus TCP Client)  <->  Modbus TCP 127.0.0.1:1502  <->  제어기 (Modbus TCP Server)
                                                                 CODESYS PLC 또는 Python
```

## 폴더

| 폴더 | 내용 |
| --- | --- |
| `ConveyorURP/` | Unity 프로젝트 (Assets, Packages, ProjectSettings). Unity 6000.5.9f1, URP |
| `ConveyorURP/BuildWin.zip` | Windows 실행 파일 |
| `ConveyorURP/BuildUbuntu.zip` | Ubuntu 실행 파일 |
| `ConveyorURP/BuildMac.app.zip` | macOS 실행 파일 |
| `AI_Training/` | Python: Modbus 서버, 데이터 수집, 지도·모방학습, 강화학습(PPO), YOLO |
| `PLC/` | CODESYS V3.5 프로젝트와 소스 |
| `Model/` | 컨베이어 3D 모델 (STEP) |

## 빠른 시작

1. 사용하는 OS의 빌드 zip을 풀고 실행합니다.
2. Python 3.12 가상환경을 만들고 패키지를 설치합니다.
   ```
   python -m venv .venv
   pip install pymodbus pandas scikit-learn matplotlib joblib gymnasium stable-baselines3 tensorboard ultralytics opencv-python flask
   ```
3. 제어기를 하나만 실행합니다. 예: `python AI_Training/conveyor_il/il_collect_manual.py`
4. Unity에서 Controller 모드로 통신을 시작합니다.

## 레지스터 맵

| 레지스터 | bit | 의미 | 방향 |
| --- | --- | --- | --- |
| HR0 | 0 / 1 / 2 | Sensor01 / Sensor02 / WorkpieceLost | Unity → 제어기 |
| HR10 | 0 / 1 / 2 | LEFT / RIGHT / RESET | 제어기 → Unity |

자세한 규칙은 `PROJECT_MAP.md`를 참고하세요.
