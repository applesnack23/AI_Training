using UnityEngine;

public class IOMapUI : MonoBehaviour
{
    // =====================================================
    // Control Mode
    // =====================================================

    [Header("Control Mode")]

    [SerializeField]
    private ControlModeManager controlModeManager;


    // =====================================================
    // Panels
    // =====================================================

    [Header("Panels")]

    [SerializeField]
    private GameObject ioMapPanel_Controller;

    [SerializeField]
    private GameObject ioMapPanel_Arduino;

    [SerializeField]
    private GameObject monitorPanel;


    // =====================================================
    // Start
    // =====================================================

    private void Start()
    {
        Close();
    }


    // =====================================================
    // IO MAP Button
    // =====================================================

    public void OpenIOMap()
    {
        HideAllPanels();


        if (controlModeManager == null)
        {
            Debug.LogError(
                "[IOMapUI] ControlModeManager is not assigned."
            );

            return;
        }


        // -------------------------------------------------
        // Controller Mode
        // -------------------------------------------------

        if (
            controlModeManager.CurrentMode
            ==
            ControlModeManager.ControlMode.Controller
        )
        {
            if (ioMapPanel_Controller != null)
            {
                ioMapPanel_Controller.SetActive(true);

                Debug.Log(
                    "[IOMapUI] OPEN CONTROLLER IO MAP"
                );
            }
        }

        // -------------------------------------------------
        // Arduino Mode
        // -------------------------------------------------

        else
        {
            if (ioMapPanel_Arduino != null)
            {
                ioMapPanel_Arduino.SetActive(true);

                Debug.Log(
                    "[IOMapUI] OPEN ARDUINO IO MAP"
                );
            }
        }
    }


    // =====================================================
    // MONITOR Button
    // =====================================================

    public void OpenMonitor()
    {
        HideAllPanels();


        if (monitorPanel != null)
        {
            monitorPanel.SetActive(true);

            Debug.Log(
                "[IOMapUI] OPEN MONITOR"
            );
        }
    }


    // =====================================================
    // CLOSE Button
    // =====================================================

    public void Close()
    {
        HideAllPanels();
    }


    // =====================================================
    // Hide All Panels
    // =====================================================

    private void HideAllPanels()
    {
        if (ioMapPanel_Controller != null)
        {
            ioMapPanel_Controller.SetActive(false);
        }


        if (ioMapPanel_Arduino != null)
        {
            ioMapPanel_Arduino.SetActive(false);
        }


        if (monitorPanel != null)
        {
            monitorPanel.SetActive(false);
        }
    }
}