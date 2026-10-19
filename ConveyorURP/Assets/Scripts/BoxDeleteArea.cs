using UnityEngine;


public class BoxDeleteArea : MonoBehaviour
{
    // =========================================================
    // Workpiece Lost
    //
    // DeleteArea_Left / DeleteArea_Right 공유
    // =========================================================

    private static bool workpieceLost = false;


    public static bool IsWorkpieceLost
    {
        get
        {
            return workpieceLost;
        }
    }


    // =========================================================
    // Trigger
    // =========================================================

    private void OnTriggerEnter(Collider other)
    {
        if (!other.CompareTag("Box"))
        {
            return;
        }


        Rigidbody rb =
            other.attachedRigidbody;


        if (rb == null)
        {
            return;
        }


        // -----------------------------------------------------
        // Workpiece Lost
        // -----------------------------------------------------

        workpieceLost = true;


        Debug.Log(
            $"[FAULT] Workpiece Lost : {gameObject.name}"
        );


        // -----------------------------------------------------
        // 물리 동작 정지
        // -----------------------------------------------------

        rb.linearVelocity =
            Vector3.zero;

        rb.angularVelocity =
            Vector3.zero;

        rb.isKinematic =
            true;

        rb.useGravity =
            false;


        // -----------------------------------------------------
        // Box 즉시 삭제 요청
        // -----------------------------------------------------

        Destroy(
            other.gameObject
        );
    }


    // =========================================================
    // Fault Reset
    // =========================================================

    public static void ResetFault()
    {
        workpieceLost = false;


        Debug.Log(
            "[FAULT] Workpiece Lost Reset"
        );
    }
}