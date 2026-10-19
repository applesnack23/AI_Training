using UnityEngine;
using UnityEngine.UI;

public class ControlModeManager : MonoBehaviour
{
    // =========================================================
    // Control Mode
    // =========================================================

    public enum ControlMode
    {
        Controller,
        Arduino
    }


    // =========================================================
    // Current Control Mode
    // =========================================================

    [Header("Current Control Mode")]
    [SerializeField]
    private ControlMode controlMode =
        ControlMode.Controller;


    // =========================================================
    // Controllers
    // =========================================================

    [Header("Controllers")]
    [SerializeField]
    private ModbusController modbusController;


    [SerializeField]
    private Esp32Bridge esp32Bridge;


    // =========================================================
    // Mode Buttons
    // =========================================================

    [Header("Mode Buttons")]
    [SerializeField]
    private Button controllerButton;


    [SerializeField]
    private Button arduinoButton;


    // =========================================================
    // Button Colors
    // =========================================================

    [Header("Button Colors")]
    [SerializeField]
    private Color selectedColor =
        new Color(
            0.2f,
            0.7f,
            1.0f,
            1.0f
        );


    [SerializeField]
    private Color normalColor =
        new Color(
            0.25f,
            0.25f,
            0.25f,
            1.0f
        );


    // =========================================================
    // Public Properties
    // =========================================================

    public ControlMode CurrentMode
    {
        get
        {
            return controlMode;
        }
    }


    public bool IsControllerMode
    {
        get
        {
            return
                controlMode
                ==
                ControlMode.Controller;
        }
    }


    public bool IsArduinoMode
    {
        get
        {
            return
                controlMode
                ==
                ControlMode.Arduino;
        }
    }


    // =========================================================
    // Unity
    // =========================================================

    private void Start()
    {
        ApplyControlMode();
    }


    // =========================================================
    // Controller Mode
    // =========================================================

    public void SetControllerMode()
    {
        controlMode =
            ControlMode.Controller;


        ApplyControlMode();
    }


    // =========================================================
    // Arduino Mode
    // =========================================================

    public void SetArduinoMode()
    {
        controlMode =
            ControlMode.Arduino;


        ApplyControlMode();
    }


    // =========================================================
    // Set Mode
    // =========================================================

    public void SetMode(
        ControlMode mode
    )
    {
        controlMode =
            mode;


        ApplyControlMode();
    }


    // =========================================================
    // Apply Control Mode
    // =========================================================

    private void ApplyControlMode()
    {
        bool controllerEnabled =
            controlMode
            ==
            ControlMode.Controller;


        bool arduinoEnabled =
            controlMode
            ==
            ControlMode.Arduino;


        // =====================================================
        // Controller Communication
        // =====================================================

        if (modbusController != null)
        {
            modbusController
                .SetCommunicationEnabled(
                    controllerEnabled
                );
        }


        // =====================================================
        // Arduino Communication
        // =====================================================

        if (esp32Bridge != null)
        {
            esp32Bridge
                .SetCommunicationEnabled(
                    arduinoEnabled
                );
        }


        // =====================================================
        // Button Color
        // =====================================================

        UpdateButtonColors();


        Debug.Log(
            "[Control Mode] "
            +
            controlMode
        );
    }


    // =========================================================
    // Button Color
    // =========================================================

    private void UpdateButtonColors()
    {
        // -----------------------------------------------------
        // Controller Button
        // -----------------------------------------------------

        if (controllerButton != null)
        {
            ColorBlock colors =
                controllerButton.colors;


            colors.normalColor =
                IsControllerMode
                    ? selectedColor
                    : normalColor;


            colors.selectedColor =
                colors.normalColor;


            colors.highlightedColor =
                colors.normalColor;


            controllerButton.colors =
                colors;
        }


        // -----------------------------------------------------
        // Arduino Button
        // -----------------------------------------------------

        if (arduinoButton != null)
        {
            ColorBlock colors =
                arduinoButton.colors;


            colors.normalColor =
                IsArduinoMode
                    ? selectedColor
                    : normalColor;


            colors.selectedColor =
                colors.normalColor;


            colors.highlightedColor =
                colors.normalColor;


            arduinoButton.colors =
                colors;
        }
    }
}