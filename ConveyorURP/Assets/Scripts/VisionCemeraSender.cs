using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

public class VisionCameraSender : MonoBehaviour
{
    [Header("Vision")]
    public RenderTexture visionRT;

    [Header("Python HTTP Server")]
    public string serverUrl = "http://127.0.0.1:8000/frame";

    [Header("Transmission")]
    public float sendInterval = 1.0f/30.0f;   // 30 FPS
    [Range(10, 100)]
    public int jpegQuality = 80;

    private Texture2D captureTexture;


    void Start()
    {
        // VisionRT 연결 확인
        if (visionRT == null)
        {
            Debug.LogError("[VISION] VisionRT가 연결되지 않았습니다.");
            enabled = false;
            return;
        }

        // VisionRT와 같은 크기의 Texture2D 생성
        captureTexture = new Texture2D(
            visionRT.width,
            visionRT.height,
            TextureFormat.RGB24,
            false
        );

        Debug.Log(
            $"[VISION] Sender Started " +
            $"{visionRT.width}x{visionRT.height}"
        );

        StartCoroutine(SendLoop());
    }


    IEnumerator SendLoop()
    {
        while (true)
        {
            yield return new WaitForSeconds(sendInterval);

            yield return SendFrame();
        }
    }


    IEnumerator SendFrame()
    {
        // 기존 RenderTexture 저장
        RenderTexture previous = RenderTexture.active;

        // VisionRT 읽기
        RenderTexture.active = visionRT;

        captureTexture.ReadPixels(
            new Rect(
                0,
                0,
                visionRT.width,
                visionRT.height
            ),
            0,
            0,
            false
        );

        captureTexture.Apply(false, false);

        // 원래 RenderTexture 복구
        RenderTexture.active = previous;

        // JPEG 변환
        byte[] jpegData =
            captureTexture.EncodeToJPG(jpegQuality);


        // HTTP POST 생성
        using (UnityWebRequest request =
               new UnityWebRequest(
                   serverUrl,
                   UnityWebRequest.kHttpVerbPOST))
        {
            request.uploadHandler =
                new UploadHandlerRaw(jpegData);

            request.downloadHandler =
                new DownloadHandlerBuffer();

            request.SetRequestHeader(
                "Content-Type",
                "image/jpeg"
            );

            // Python으로 전송
            yield return request.SendWebRequest();


            if (request.result ==
                UnityWebRequest.Result.Success)
            {
                // 통신 확인용
                Debug.Log(
                    $"[VISION] Sent : {jpegData.Length} bytes"
                );
            }
            else
            {
                Debug.LogWarning(
                    "[VISION] HTTP Error : "
                    + request.error
                );
            }
        }
    }


    void OnDestroy()
    {
        if (captureTexture != null)
        {
            Destroy(captureTexture);
        }
    }
}