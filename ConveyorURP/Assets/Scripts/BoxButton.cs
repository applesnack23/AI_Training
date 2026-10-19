using UnityEngine;
using UnityEngine.EventSystems;

public class BoxButton : MonoBehaviour,
    IPointerDownHandler,
    IDragHandler,
    IPointerUpHandler
{
    [Header("Box")]
    [SerializeField] private GameObject boxPrefab;

    [Header("Spawn Position")]
    [SerializeField] private float fixedX = 0.355f;
    [SerializeField] private float spawnY = 0.06f;
    [SerializeField] private float spawnZ = -1.3f;

    private GameObject currentBox;
    private Rigidbody currentRigidbody;
    private Camera mainCamera;

    private void Awake()
    {
        mainCamera = Camera.main;
    }

    // =========================================================
    // 마우스를 누르는 순간
    // =========================================================

    public void OnPointerDown(PointerEventData eventData)
    {
        // Box 생성
        Vector3 spawnPosition =
            new Vector3(fixedX, spawnY, spawnZ);

        currentBox = Instantiate(
            boxPrefab,
            spawnPosition,
            Quaternion.identity
        );

        currentRigidbody =
            currentBox.GetComponent<Rigidbody>();

        if (currentRigidbody != null)
        {
            // 마우스로 들고 있는 동안 물리 동작 중지
            currentRigidbody.linearVelocity = Vector3.zero;
            currentRigidbody.angularVelocity = Vector3.zero;

            currentRigidbody.useGravity = false;
            currentRigidbody.isKinematic = true;
        }

        // 생성되자마자 현재 마우스 위치로 이동
        MoveBox(eventData.position);
    }


    // =========================================================
    // 마우스를 누른 상태에서 움직일 때
    // =========================================================

    public void OnDrag(PointerEventData eventData)
    {
        if (currentBox == null)
            return;

        MoveBox(eventData.position);
    }


    // =========================================================
    // 마우스를 놓는 순간
    // =========================================================

    public void OnPointerUp(PointerEventData eventData)
    {
        if (currentBox == null)
            return;

        if (currentRigidbody != null)
        {
            // 다시 물리 동작 시작
            currentRigidbody.isKinematic = false;
            currentRigidbody.useGravity = true;
        }

        currentBox = null;
        currentRigidbody = null;
    }


    // =========================================================
    // Box를 마우스 위치로 이동
    // =========================================================

    private void MoveBox(Vector2 mousePosition)
    {
        if (currentBox == null || mainCamera == null)
            return;

        // 마우스 위치에서 3D 공간으로 Ray 생성
        Ray ray =
            mainCamera.ScreenPointToRay(mousePosition);

        // X = fixedX인 가상의 평면 생성
        Plane dragPlane =
            new Plane(
                Vector3.right,
                new Vector3(fixedX, 0f, 0f)
            );

        // Ray와 평면의 교점 계산
        if (dragPlane.Raycast(ray, out float distance))
        {
            Vector3 position =
                ray.GetPoint(distance);

            // X는 항상 고정
            currentBox.transform.position =
                new Vector3(
                    fixedX,
                    position.y,
                    position.z
                );
        }
    }
}