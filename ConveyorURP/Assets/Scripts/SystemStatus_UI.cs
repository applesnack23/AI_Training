using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class SystemStatus_UI : MonoBehaviour
{
    // =========================================================
    // Control Mode
    // =========================================================

    [Header("Control Mode")]
    [SerializeField]
    private ControlModeManager controlModeManager;


    // =========================================================
    // Controllers
    // =========================================================

    [Header("Controller")]
    [SerializeField]
    private ModbusController modbusController;


    [Header("Arduino")]
    [SerializeField]
    private Esp32Bridge esp32Bridge;


    // =========================================================
    // Sensor Trigger
    // =========================================================

    [Header("Sensor Trigger")]
    [SerializeField]
    private SensorTrigger sensor01;

    [SerializeField]
    private SensorTrigger sensor02;


    // =========================================================
    // Connection
    // =========================================================

    [Header("Connection UI")]
    [SerializeField]
    private Image connectionLamp;

    [SerializeField]
    private TMP_Text connectionText;


    // =========================================================
    // Move Left / Right
    // =========================================================

    [Header("Move Left UI")]
    [SerializeField]
    private Image moveLeftLamp;

    [SerializeField]
    private TMP_Text moveLeftText;


    [Header("Move Right UI")]
    [SerializeField]
    private Image moveRightLamp;

    [SerializeField]
    private TMP_Text moveRightText;


    // =========================================================
    // Sensor 01 UI - Main
    // =========================================================

    [Header("Sensor 01 - Main UI")]
    [SerializeField]
    private Image sensor01MainLamp;

    [SerializeField]
    private TMP_Text sensor01MainText;


    // =========================================================
    // Sensor 01 UI - System Status
    // =========================================================

    [Header("Sensor 01 - System Status")]
    [SerializeField]
    private Image sensor01StatusLamp;

    [SerializeField]
    private TMP_Text sensor01StatusText;


    // =========================================================
    // Sensor 02 UI - Main
    // =========================================================

    [Header("Sensor 02 - Main UI")]
    [SerializeField]
    private Image sensor02MainLamp;

    [SerializeField]
    private TMP_Text sensor02MainText;


    // =========================================================
    // Sensor 02 UI - System Status
    // =========================================================

    [Header("Sensor 02 - System Status")]
    [SerializeField]
    private Image sensor02StatusLamp;

    [SerializeField]
    private TMP_Text sensor02StatusText;


    // =========================================================
    // Color
    // =========================================================

    [Header("Connection Color")]
    [SerializeField]
    private Color connectedColor = Color.green;

    [SerializeField]
    private Color disconnectedColor = Color.red;


    [Header("Status Color")]
    [SerializeField]
    private Color statusOnColor = Color.green;

    [SerializeField]
    private Color statusOffColor = Color.gray;


    // =========================================================
    // Unity
    // =========================================================

    private void Start()
    {
        UpdateConnectionUI();
        UpdateMoveUI();
        UpdateSensorUI();
    }


    private void Update()
    {
        UpdateConnectionUI();
        UpdateMoveUI();
        UpdateSensorUI();
    }


    // =========================================================
    // Connection
    // =========================================================

    private void UpdateConnectionUI()
    {
        if (controlModeManager == null)
        {
            return;
        }


        bool connected = false;


        // =====================================================
        // Controller Mode
        // =====================================================

        if (controlModeManager.IsControllerMode)
        {
            if (modbusController != null)
            {
                connected =
                    modbusController.IsConnected;
            }
        }


        // =====================================================
        // Arduino Mode
        // =====================================================

        else if (controlModeManager.IsArduinoMode)
        {
            if (esp32Bridge != null)
            {
                connected =
                    esp32Bridge.IsConnected;
            }
        }


        // =====================================================
        // UI
        // =====================================================

        if (connected)
        {
            if (connectionLamp != null)
            {
                connectionLamp.color =
                    connectedColor;
            }


            if (connectionText != null)
            {
                connectionText.text =
                    "CONNECTED";

                connectionText.color =
                    connectedColor;
            }
        }
        else
        {
            if (connectionLamp != null)
            {
                connectionLamp.color =
                    disconnectedColor;
            }


            if (connectionText != null)
            {
                connectionText.text =
                    "DISCONNECTED";

                connectionText.color =
                    disconnectedColor;
            }
        }
    }


    // =========================================================
    // Move Left / Right
    // =========================================================

    private void UpdateMoveUI()
    {
        if (controlModeManager == null)
        {
            return;
        }


        bool moveLeft = false;
        bool moveRight = false;


        // =====================================================
        // Controller Mode
        // =====================================================

        if (controlModeManager.IsControllerMode)
        {
            if (modbusController == null)
            {
                UpdateStatusDisplay(
                    moveLeftLamp,
                    moveLeftText,
                    false
                );


                UpdateStatusDisplay(
                    moveRightLamp,
                    moveRightText,
                    false
                );


                return;
            }


            // Controller -> Unity
            //
            // fromController[0].0 = MOVE LEFT
            // fromController[0].1 = MOVE RIGHT

            moveLeft =
                modbusController.GetFromControllerBit(
                    0,
                    0
                );


            moveRight =
                modbusController.GetFromControllerBit(
                    0,
                    1
                );
        }


        // =====================================================
        // Arduino Mode
        // =====================================================

        else if (controlModeManager.IsArduinoMode)
        {
            if (esp32Bridge == null)
            {
                UpdateStatusDisplay(
                    moveLeftLamp,
                    moveLeftText,
                    false
                );


                UpdateStatusDisplay(
                    moveRightLamp,
                    moveRightText,
                    false
                );


                return;
            }


            // Arduino -> Unity
            //
            // GPIO21 = MOVE LEFT
            // GPIO22 = MOVE RIGHT

            moveLeft =
                esp32Bridge.MoveLeft;


            moveRight =
                esp32Bridge.MoveRight;
        }


        // =====================================================
        // Update UI
        // =====================================================

        UpdateStatusDisplay(
            moveLeftLamp,
            moveLeftText,
            moveLeft
        );


        UpdateStatusDisplay(
            moveRightLamp,
            moveRightText,
            moveRight
        );
    }


    // =========================================================
    // Sensor
    // =========================================================

    private void UpdateSensorUI()
    {
        // =====================================================
        // Sensor 01
        // =====================================================

        if (sensor01 != null)
        {
            bool detected =
                sensor01.IsDetected;


            UpdateStatusDisplay(
                sensor01MainLamp,
                sensor01MainText,
                detected
            );


            UpdateStatusDisplay(
                sensor01StatusLamp,
                sensor01StatusText,
                detected
            );
        }


        // =====================================================
        // Sensor 02
        // =====================================================

        if (sensor02 != null)
        {
            bool detected =
                sensor02.IsDetected;


            UpdateStatusDisplay(
                sensor02MainLamp,
                sensor02MainText,
                detected
            );


            UpdateStatusDisplay(
                sensor02StatusLamp,
                sensor02StatusText,
                detected
            );
        }
    }


    // =========================================================
    // Common Status Display
    // =========================================================

    private void UpdateStatusDisplay(
        Image lamp,
        TMP_Text text,
        bool isOn
    )
    {
        if (lamp != null)
        {
            lamp.color =
                isOn
                    ? statusOnColor
                    : statusOffColor;
        }


        if (text != null)
        {
            text.text =
                isOn
                    ? "ON"
                    : "OFF";


            text.color =
                isOn
                    ? statusOnColor
                    : statusOffColor;
        }
    }
}