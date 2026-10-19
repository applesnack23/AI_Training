using UnityEngine;

public class SensorTrigger : MonoBehaviour
{
    [SerializeField] private bool isDetected = false;
    [SerializeField] private int detectedCount = 0;

    public bool IsDetected => isDetected;

    private void OnTriggerEnter(Collider other)
    {
        detectedCount++;

        isDetected = detectedCount > 0;
    }

    private void OnTriggerExit(Collider other)
    {
        detectedCount--;

        // 음수가 되는 것 방지
        if (detectedCount < 0)
            detectedCount = 0;

        isDetected = detectedCount > 0;
    }
}