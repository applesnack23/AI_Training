using System.Collections;
using System.IO;
using UnityEngine;

public class YOLO_DatasetCapture : MonoBehaviour
{
    // =========================================================
    // Inspector
    // =========================================================

    [Header("Vision Camera")]
    [Tooltip("YOLO 학습 이미지를 촬영할 VisionCamera")]
    public Camera visionCamera;


    [Header("Target Box")]
    [Tooltip("런타임에 생성되는 Box의 Tag")]
    public string targetTag = "Box";


    [Header("Dataset")]
    [Tooltip("프로젝트 루트에 생성될 Dataset 폴더")]
    public string datasetFolder = "YOLO_Dataset";


    [Header("Image")]
    public int imageWidth = 640;
    public int imageHeight = 480;
    public int jpegQuality = 95;


    [Header("Capture")]
    public KeyCode captureKey = KeyCode.Space;

    [Tooltip("자동 캡처")]
    public bool autoCapture = false;

    [Tooltip("자동 캡처 간격(초)")]
    public float captureInterval = 0.2f;


    // =========================================================
    // Private
    // =========================================================

    private string imageFolder;
    private string labelFolder;

    private int imageIndex = 0;

    private float captureTimer = 0f;

    private bool isCapturing = false;


    // =========================================================
    // Start
    // =========================================================

    void Start()
    {
        // -----------------------------------------------------
        // VisionCamera 확인
        // -----------------------------------------------------

        if (visionCamera == null)
        {
            Debug.LogError(
                "[YOLO] VisionCamera가 연결되지 않았습니다."
            );

            enabled = false;
            return;
        }


        // -----------------------------------------------------
        // Dataset Root
        //
        // Unity Project/
        // └── YOLO_Dataset/
        //
        // -----------------------------------------------------

        string rootFolder = Path.GetFullPath(
            Path.Combine(
                Application.dataPath,
                "..",
                datasetFolder
            )
        );


        imageFolder = Path.Combine(
            rootFolder,
            "images"
        );


        labelFolder = Path.Combine(
            rootFolder,
            "labels"
        );


        Directory.CreateDirectory(
            imageFolder
        );


        Directory.CreateDirectory(
            labelFolder
        );


        // -----------------------------------------------------
        // 다음 이미지 번호 계산
        // -----------------------------------------------------

        imageIndex = GetNextImageIndex();


        // -----------------------------------------------------
        // Log
        // -----------------------------------------------------

        Debug.Log(
            "[YOLO] Dataset Capture Ready"
        );

        Debug.Log(
            "[YOLO] Camera : "
            + visionCamera.name
        );

        Debug.Log(
            "[YOLO] Dataset : "
            + rootFolder
        );

        Debug.Log(
            "[YOLO] Next Index : "
            + imageIndex
        );

        Debug.Log(
            "[YOLO] SPACE = Capture / A = Auto ON/OFF"
        );
    }


    // =========================================================
    // Update
    // =========================================================

    void Update()
    {
        // -----------------------------------------------------
        // SPACE : 수동 Capture
        // -----------------------------------------------------

        if (Input.GetKeyDown(captureKey))
        {
            StartCoroutine(
                CaptureDataset()
            );
        }


        // -----------------------------------------------------
        // A : Auto Capture ON / OFF
        // -----------------------------------------------------

        if (Input.GetKeyDown(KeyCode.A))
        {
            autoCapture = !autoCapture;

            captureTimer = 0f;


            Debug.Log(
                "[YOLO] Auto Capture : "
                + (
                    autoCapture
                    ? "ON"
                    : "OFF"
                )
            );
        }


        // -----------------------------------------------------
        // Auto Capture
        // -----------------------------------------------------

        if (autoCapture)
        {
            captureTimer += Time.deltaTime;


            if (captureTimer >= captureInterval)
            {
                captureTimer = 0f;


                if (!isCapturing)
                {
                    StartCoroutine(
                        CaptureDataset()
                    );
                }
            }
        }
    }


    // =========================================================
    // Capture Dataset
    // =========================================================

    IEnumerator CaptureDataset()
    {
        if (isCapturing)
        {
            yield break;
        }


        isCapturing = true;


        // 현재 프레임의 모든 Transform 업데이트가 끝난 뒤 촬영
        yield return new WaitForEndOfFrame();


        // -----------------------------------------------------
        // 런타임 Box 검색
        // -----------------------------------------------------

        GameObject targetBox = FindTargetBox();


        // -----------------------------------------------------
        // Filename
        // -----------------------------------------------------

        string fileName =
            $"box_{imageIndex:D6}";


        string imagePath =
            Path.Combine(
                imageFolder,
                fileName + ".jpg"
            );


        string labelPath =
            Path.Combine(
                labelFolder,
                fileName + ".txt"
            );


        // -----------------------------------------------------
        // VisionCamera 전용 RenderTexture
        // -----------------------------------------------------

        RenderTexture renderTexture =
            new RenderTexture(
                imageWidth,
                imageHeight,
                24,
                RenderTextureFormat.ARGB32
            );


        RenderTexture previousTarget =
            visionCamera.targetTexture;


        RenderTexture previousActive =
            RenderTexture.active;


        // -----------------------------------------------------
        // VisionCamera Render
        // -----------------------------------------------------

        visionCamera.targetTexture =
            renderTexture;


        RenderTexture.active =
            renderTexture;


        visionCamera.Render();


        // -----------------------------------------------------
        // RenderTexture → Texture2D
        // -----------------------------------------------------

        Texture2D image =
            new Texture2D(
                imageWidth,
                imageHeight,
                TextureFormat.RGB24,
                false
            );


        image.ReadPixels(
            new Rect(
                0,
                0,
                imageWidth,
                imageHeight
            ),
            0,
            0
        );


        image.Apply();


        // -----------------------------------------------------
        // JPG 저장
        // -----------------------------------------------------

        byte[] jpgData =
            image.EncodeToJPG(
                jpegQuality
            );


        File.WriteAllBytes(
            imagePath,
            jpgData
        );


        // -----------------------------------------------------
        // YOLO Label 생성
        // -----------------------------------------------------

        bool labelCreated = false;


        if (targetBox != null)
        {
            if (
                TryGetYoloBoundingBox(
                    targetBox,
                    visionCamera,
                    out float centerX,
                    out float centerY,
                    out float width,
                    out float height
                )
            )
            {
                // ---------------------------------------------
                // YOLO
                //
                // class centerX centerY width height
                //
                // Class 0 = BOX
                // ---------------------------------------------

                string label =
                    $"0 "
                    + $"{centerX:F6} "
                    + $"{centerY:F6} "
                    + $"{width:F6} "
                    + $"{height:F6}";


                File.WriteAllText(
                    labelPath,
                    label
                );


                labelCreated = true;


                Debug.Log(
                    $"[YOLO] SAVE : {fileName}"
                    + $" | BOX"
                    + $" | X={centerX:F3}"
                    + $" Y={centerY:F3}"
                    + $" W={width:F3}"
                    + $" H={height:F3}"
                );
            }
        }


        // -----------------------------------------------------
        // Box가 없거나 화면에 보이지 않는 경우
        //
        // Negative Sample
        // 빈 TXT 생성
        // -----------------------------------------------------

        if (!labelCreated)
        {
            File.WriteAllText(
                labelPath,
                string.Empty
            );


            Debug.Log(
                $"[YOLO] SAVE : {fileName}"
                + " | NO BOX"
                + " | Negative Sample"
            );
        }


        // -----------------------------------------------------
        // Restore
        // -----------------------------------------------------

        visionCamera.targetTexture =
            previousTarget;


        RenderTexture.active =
            previousActive;


        // -----------------------------------------------------
        // Memory Release
        // -----------------------------------------------------

        Destroy(image);


        renderTexture.Release();

        Destroy(renderTexture);


        // -----------------------------------------------------
        // Next
        // -----------------------------------------------------

        imageIndex++;


        isCapturing = false;
    }


    // =========================================================
    // Find Target Box
    // =========================================================

    GameObject FindTargetBox()
    {
        try
        {
            return GameObject.FindGameObjectWithTag(
                targetTag
            );
        }
        catch (UnityException)
        {
            Debug.LogError(
                $"[YOLO] Tag '{targetTag}'가 존재하지 않습니다."
            );

            return null;
        }
    }


    // =========================================================
    // 3D Object → YOLO Bounding Box
    // =========================================================

    bool TryGetYoloBoundingBox(
        GameObject target,
        Camera cam,
        out float centerX,
        out float centerY,
        out float width,
        out float height
    )
    {
        centerX = 0f;
        centerY = 0f;
        width = 0f;
        height = 0f;


        // -----------------------------------------------------
        // Renderer 검색
        // -----------------------------------------------------

        Renderer[] renderers =
            target.GetComponentsInChildren<Renderer>();


        if (renderers.Length == 0)
        {
            return false;
        }


        // -----------------------------------------------------
        // 전체 Renderer Bounds 결합
        // -----------------------------------------------------

        Bounds bounds =
            renderers[0].bounds;


        for (int i = 1; i < renderers.Length; i++)
        {
            bounds.Encapsulate(
                renderers[i].bounds
            );
        }


        Vector3 center =
            bounds.center;


        Vector3 extents =
            bounds.extents;


        // -----------------------------------------------------
        // Bounds의 8개 Corner
        // -----------------------------------------------------

        Vector3[] corners =
        {
            center + new Vector3(
                -extents.x,
                -extents.y,
                -extents.z
            ),

            center + new Vector3(
                -extents.x,
                -extents.y,
                 extents.z
            ),

            center + new Vector3(
                -extents.x,
                 extents.y,
                -extents.z
            ),

            center + new Vector3(
                -extents.x,
                 extents.y,
                 extents.z
            ),

            center + new Vector3(
                 extents.x,
                -extents.y,
                -extents.z
            ),

            center + new Vector3(
                 extents.x,
                -extents.y,
                 extents.z
            ),

            center + new Vector3(
                 extents.x,
                 extents.y,
                -extents.z
            ),

            center + new Vector3(
                 extents.x,
                 extents.y,
                 extents.z
            )
        };


        // -----------------------------------------------------
        // Viewport 좌표
        //
        // (0,0) = 좌측 아래
        // (1,1) = 우측 위
        //
        // RenderTexture 크기와 관계없이 0~1이므로
        // Bounding Box 계산에 더 적합
        // -----------------------------------------------------

        float minX = float.MaxValue;
        float minY = float.MaxValue;

        float maxX = float.MinValue;
        float maxY = float.MinValue;


        bool hasPointInFront = false;


        foreach (Vector3 corner in corners)
        {
            Vector3 viewportPoint =
                cam.WorldToViewportPoint(
                    corner
                );


            // 카메라 뒤
            if (viewportPoint.z <= 0f)
            {
                continue;
            }


            hasPointInFront = true;


            minX = Mathf.Min(
                minX,
                viewportPoint.x
            );


            minY = Mathf.Min(
                minY,
                viewportPoint.y
            );


            maxX = Mathf.Max(
                maxX,
                viewportPoint.x
            );


            maxY = Mathf.Max(
                maxY,
                viewportPoint.y
            );
        }


        if (!hasPointInFront)
        {
            return false;
        }


        // -----------------------------------------------------
        // 화면 밖에 완전히 존재하는지 확인
        // -----------------------------------------------------

        if (
            maxX <= 0f
            || minX >= 1f
            || maxY <= 0f
            || minY >= 1f
        )
        {
            return false;
        }


        // -----------------------------------------------------
        // 화면 영역으로 Clamp
        // -----------------------------------------------------

        minX = Mathf.Clamp01(minX);
        maxX = Mathf.Clamp01(maxX);

        minY = Mathf.Clamp01(minY);
        maxY = Mathf.Clamp01(maxY);


        if (
            maxX <= minX
            || maxY <= minY
        )
        {
            return false;
        }


        // -----------------------------------------------------
        // YOLO X
        // -----------------------------------------------------

        centerX =
            (minX + maxX)
            * 0.5f;


        width =
            maxX - minX;


        // -----------------------------------------------------
        // Unity Y
        //
        // Unity Viewport
        // Bottom = 0
        // Top    = 1
        //
        // YOLO
        // Top    = 0
        // Bottom = 1
        //
        // Y 반전
        // -----------------------------------------------------

        float unityCenterY =
            (minY + maxY)
            * 0.5f;


        centerY =
            1f - unityCenterY;


        height =
            maxY - minY;


        // -----------------------------------------------------
        // 최종 Clamp
        // -----------------------------------------------------

        centerX = Mathf.Clamp01(centerX);
        centerY = Mathf.Clamp01(centerY);

        width = Mathf.Clamp01(width);
        height = Mathf.Clamp01(height);


        return true;
    }


    // =========================================================
    // Next Image Index
    // =========================================================

    int GetNextImageIndex()
    {
        int maxIndex = -1;


        string[] files =
            Directory.GetFiles(
                imageFolder,
                "box_*.jpg"
            );


        foreach (string file in files)
        {
            string fileName =
                Path.GetFileNameWithoutExtension(
                    file
                );


            string number =
                fileName.Replace(
                    "box_",
                    ""
                );


            if (
                int.TryParse(
                    number,
                    out int index
                )
            )
            {
                if (index > maxIndex)
                {
                    maxIndex = index;
                }
            }
        }


        return maxIndex + 1;
    }


    // =========================================================
    // 종료
    // =========================================================

    void OnDestroy()
    {
        Debug.Log(
            "[YOLO] Dataset Capture End"
        );
    }
}