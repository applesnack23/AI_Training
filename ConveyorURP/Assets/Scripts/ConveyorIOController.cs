using UnityEngine;

public class ConveyorIOController : MonoBehaviour
{
    // =========================================================
    // Controller
    // =========================================================

    [Header("Control Mode")]
    [SerializeField]
    private ControlModeManager controlModeManager;


    [Header("Controller")]
    [SerializeField]
    private ModbusController modbusController;


    [Header("Arduino")]
    [SerializeField]
    private Esp32Bridge esp32Bridge;


    // =========================================================
    // Sensor
    // =========================================================

    [Header("Sensor")]
    [SerializeField]
    private SensorTrigger sensor01;

    [SerializeField]
    private SensorTrigger sensor02;


    // =========================================================
    // Unity
    // =========================================================

    private void Update()
    {
        if (controlModeManager == null)
        {
            return;
        }


        // =====================================================
        // Sensor 상태
        // =====================================================

        bool sensor01Detected =
            sensor01 != null
            &&
            sensor01.IsDetected;


        bool sensor02Detected =
            sensor02 != null
            &&
            sensor02.IsDetected;


        // =====================================================
        // Controller Mode
        // =====================================================

        if (controlModeManager.IsControllerMode)
        {
            UpdateController(
                sensor01Detected,
                sensor02Detected
            );


            return;
        }


        // =====================================================
        // Arduino Mode
        // =====================================================

        if (controlModeManager.IsArduinoMode)
        {
            UpdateArduino(
                sensor01Detected,
                sensor02Detected
            );
        }
    }


    // =========================================================
    // Controller
    // =========================================================

    private void UpdateController(
        bool sensor01Detected,
        bool sensor02Detected
    )
    {
        if (modbusController == null)
        {
            return;
        }


        // -----------------------------------------------------
        // SENSOR 01
        //
        // toController[0].0
        // -----------------------------------------------------

        modbusController.SetToControllerBit(
            0,
            0,
            sensor01Detected
        );


        // -----------------------------------------------------
        // SENSOR 02
        //
        // toController[0].1
        // -----------------------------------------------------

        modbusController.SetToControllerBit(
            0,
            1,
            sensor02Detected
        );

        // -----------------------------------------------------
        // WORKPIECE LIST
        //
        // toController[0].2
        // -----------------------------------------------------

        modbusController.SetToControllerBit(
            0,
            2,
            BoxDeleteArea.IsWorkpieceLost
        );
    }


    // =========================================================
    // Arduino
    // =========================================================

    private void UpdateArduino(
        bool sensor01Detected,
        bool sensor02Detected
    )
    {
        if (esp32Bridge == null)
        {
            return;
        }


        // -----------------------------------------------------
        // SENSOR 01
        //
        // Unity
        //   ↓
        // Esp32Bridge
        //   ↓
        // GPIO25
        //   ↓
        // GPIO18
        // -----------------------------------------------------

        esp32Bridge.SetSensor01(
            sensor01Detected
        );


        // -----------------------------------------------------
        // SENSOR 02
        //
        // Unity
        //   ↓
        // Esp32Bridge
        //   ↓
        // GPIO26
        //   ↓
        // GPIO19
        // -----------------------------------------------------

        esp32Bridge.SetSensor02(
            sensor02Detected
        );
    }
}