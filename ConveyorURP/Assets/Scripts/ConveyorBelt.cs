using System.Collections.Generic;
using UnityEngine;

public class ConveyorBelt : MonoBehaviour
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
    // Conveyor
    // =========================================================

    [Header("Conveyor")]
    [SerializeField]
    private float moveSpeed = 0.05f;


    // =========================================================
    // Box
    // =========================================================

    private readonly HashSet<Rigidbody> boxesOnBelt =
        new HashSet<Rigidbody>();


    // =========================================================
    // Unity
    // =========================================================

    private void FixedUpdate()
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
        // Stop Condition
        //
        // LEFT  RIGHT
        //  0      0   -> STOP
        //  1      1   -> STOP
        // =====================================================

        if (moveLeft == moveRight)
        {
            return;
        }


        // =====================================================
        // Direction
        // =====================================================

        float direction =
            moveLeft
                ? -1.0f
                : 1.0f;


        // =====================================================
        // Move Box
        // =====================================================

        foreach (Rigidbody rb in boxesOnBelt)
        {
            if (rb == null)
            {
                continue;
            }


            // Sleep 상태라면 깨움

            rb.WakeUp();


            Vector3 position =
                rb.position;


            position.z +=
                direction
                *
                moveSpeed
                *
                Time.fixedDeltaTime;


            rb.MovePosition(
                position
            );
        }
    }


    // =========================================================
    // Box Enter
    // =========================================================

    private void OnCollisionEnter(
        Collision collision
    )
    {
        if (
            !collision.gameObject.CompareTag(
                "Box"
            )
        )
        {
            return;
        }


        Rigidbody rb =
            collision.rigidbody;


        if (rb == null)
        {
            return;
        }


        boxesOnBelt.Add(
            rb
        );
    }


    // =========================================================
    // Box Exit
    // =========================================================

    private void OnCollisionExit(
        Collision collision
    )
    {
        if (
            !collision.gameObject.CompareTag(
                "Box"
            )
        )
        {
            return;
        }


        Rigidbody rb =
            collision.rigidbody;


        if (rb == null)
        {
            return;
        }


        boxesOnBelt.Remove(
            rb
        );
    }
}