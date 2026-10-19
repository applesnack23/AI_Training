using UnityEngine;

public class ConveyorResetController : MonoBehaviour
{
    [Header("References")]
    public ModbusController modbusController;

    [Header("Box")]
    public GameObject boxPrefab;
    public Transform resetPoint;

    private bool previousReset = false;


    void Update()
    {
        if (modbusController == null)
            return;

        if (boxPrefab == null)
            return;

        if (resetPoint == null)
            return;


        // HR10
        ushort commandWord =
            modbusController.fromController[0];


        // HR10.bit2 = RESET
        bool reset =
            (commandWord & 0x0004) != 0;


        // Rising Edge
        if (reset && !previousReset)
        {
            ResetBox();
        }


        previousReset = reset;
    }


    // ==================================================
    // Box Reset
    // ==================================================

    public void ResetBox()
    {
        // Workpiece Lost Fault Reset
        BoxDeleteArea.ResetFault();

        // 현재 Scene에서 Box 찾기
        GameObject box =
            GameObject.FindGameObjectWithTag("Box");


        // --------------------------------------------------
        // Box가 없으면 새로 생성
        // --------------------------------------------------

        if (box == null)
        {
            box = Instantiate(
                boxPrefab,
                resetPoint.position,
                resetPoint.rotation
            );

            Debug.Log(
                "[RESET] Box가 없어서 새로 생성했습니다."
            );
        }

        // --------------------------------------------------
        // Box가 있으면 기존 Box 사용
        // --------------------------------------------------

        else
        {
            box.transform.SetPositionAndRotation(
                resetPoint.position,
                resetPoint.rotation
            );

            Debug.Log(
                "[RESET] 기존 Box를 초기 위치로 이동했습니다."
            );
        }


        // --------------------------------------------------
        // Rigidbody 초기화
        // --------------------------------------------------

        Rigidbody rb =
            box.GetComponent<Rigidbody>();

        if (rb != null)
        {
            rb.linearVelocity =
                Vector3.zero;

            rb.angularVelocity =
                Vector3.zero;
        }
    }
}