using UnityEngine;
using UnityEngine.InputSystem;

public class BoxInteract : MonoBehaviour
{
    [Header("Drag")]
    [SerializeField] private float fixedX = 0.355f;

    [Header("Double Click")]
    [SerializeField] private float doubleClickTime = 0.3f;

    private Rigidbody rb;
    private Camera mainCamera;

    private bool isDragging = false;
    private float lastClickTime = -1f;

    private void Awake()
    {
        rb = GetComponent<Rigidbody>();
        mainCamera = Camera.main;
    }

    private void OnMouseDown()
    {
        // 더블클릭
        if (Time.time - lastClickTime <= doubleClickTime)
        {
            DeleteBox();
            return;
        }

        lastClickTime = Time.time;

        StartDragging();
    }

    private void OnMouseDrag()
    {
        if (!isDragging)
            return;

        MoveWithMouse();
    }

    private void OnMouseUp()
    {
        if (!isDragging)
            return;

        StopDragging();
    }

    private void StartDragging()
    {
        isDragging = true;

        if (rb != null)
        {
            rb.linearVelocity = Vector3.zero;
            rb.angularVelocity = Vector3.zero;

            rb.useGravity = false;
            rb.isKinematic = true;
        }
    }

    private void StopDragging()
    {
        isDragging = false;

        if (rb != null)
        {
            rb.isKinematic = false;
            rb.useGravity = true;
        }
    }

    private void MoveWithMouse()
    {
        if (mainCamera == null)
            return;

        if (Mouse.current == null)
            return;

        // New Input System에서 마우스 위치 가져오기
        Vector2 mousePosition =
            Mouse.current.position.ReadValue();

        Ray ray =
            mainCamera.ScreenPointToRay(mousePosition);

        // X = 0.355 평면
        Plane dragPlane =
            new Plane(
                Vector3.right,
                new Vector3(fixedX, 0f, 0f)
            );

        if (dragPlane.Raycast(ray, out float distance))
        {
            Vector3 position =
                ray.GetPoint(distance);

            transform.position =
                new Vector3(
                    fixedX,
                    position.y,
                    position.z
                );
        }
    }

    private void DeleteBox()
    {
        isDragging = false;

        if (rb != null)
        {
            rb.isKinematic = true;
            rb.useGravity = false;
        }

        // 센서 영역 밖으로 먼저 이동
        transform.position =
            new Vector3(
                fixedX,
                10f,
                10f
            );

        Destroy(gameObject, 0.1f);
    }
}