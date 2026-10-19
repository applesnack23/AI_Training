using System.Collections;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public class ArduinoDebugMonitor : MonoBehaviour
{
    // =====================================================
    // UI
    // =====================================================

    [Header("UI")]

    [SerializeField]
    private TMP_Text debugText;

    [SerializeField]
    private ScrollRect scrollRect;

    [SerializeField]
    private RectTransform contentRect;


    // =====================================================
    // Settings
    // =====================================================

    [Header("Settings")]

    [SerializeField]
    private int maxLines = 100;

    [SerializeField]
    private bool autoScroll = true;

    [SerializeField]
    private bool showSystemMessages = true;


    // =====================================================
    // Log Buffer
    // =====================================================

    private readonly Queue<string> lines =
        new Queue<string>();


    // =====================================================
    // Scroll Coroutine
    // =====================================================

    private Coroutine scrollCoroutine;


    // =====================================================
    // Start
    // =====================================================

    private void Start()
    {
        if (debugText != null)
        {
            debugText.text = "";
        }

        RefreshLayoutImmediate();
    }


    // =====================================================
    // Add Message
    // =====================================================

    public void AddMessage(string message)
    {
        if (string.IsNullOrEmpty(message))
        {
            return;
        }

        string normalized =
            message
            .Replace("\r\n", "\n")
            .Replace('\r', '\n');

        string[] messageLines =
            normalized.Split('\n');

        foreach (string line in messageLines)
        {
            AddLine(line);
        }

        RefreshText();
    }


    // =====================================================
    // Add System Message
    // =====================================================

    public void AddSystemMessage(string message)
    {
        if (!showSystemMessages)
        {
            return;
        }

        AddLine(
            "[SYSTEM] " + message
        );

        RefreshText();
    }


    // =====================================================
    // Add Line
    // =====================================================

    private void AddLine(string line)
    {
        lines.Enqueue(line);

        while (lines.Count > maxLines)
        {
            lines.Dequeue();
        }
    }


    // =====================================================
    // Refresh Text
    // =====================================================

    private void RefreshText()
    {
        if (debugText == null)
        {
            return;
        }

        debugText.text =
            string.Join(
                "\n",
                lines
            );

        // TMP 내부 geometry 갱신
        debugText.ForceMeshUpdate();

        // 기존 Auto Scroll 작업 중이면 중지
        if (scrollCoroutine != null)
        {
            StopCoroutine(
                scrollCoroutine
            );
        }

        // Layout 계산이 완료된 뒤
        // 맨 아래로 이동
        scrollCoroutine =
            StartCoroutine(
                RefreshAndScrollToBottom()
            );
    }


    // =====================================================
    // Refresh Layout + Auto Scroll
    // =====================================================

    private IEnumerator RefreshAndScrollToBottom()
    {
        // -------------------------------------------------
        // 현재 프레임의 UI 변경을 먼저 반영
        // -------------------------------------------------

        Canvas.ForceUpdateCanvases();

        if (contentRect != null)
        {
            LayoutRebuilder.ForceRebuildLayoutImmediate(
                contentRect
            );
        }

        Canvas.ForceUpdateCanvases();


        // -------------------------------------------------
        // 한 프레임 대기
        //
        // Content Size Fitter / Layout Group의 계산이
        // 완전히 끝난 다음 ScrollRect를 움직인다.
        // -------------------------------------------------

        yield return null;


        // -------------------------------------------------
        // 다시 한번 Layout 확정
        // -------------------------------------------------

        Canvas.ForceUpdateCanvases();

        if (contentRect != null)
        {
            LayoutRebuilder.ForceRebuildLayoutImmediate(
                contentRect
            );
        }

        Canvas.ForceUpdateCanvases();


        // -------------------------------------------------
        // 최신 로그가 보이도록 맨 아래로 이동
        // -------------------------------------------------

        if (
            autoScroll
            &&
            scrollRect != null
        )
        {
            scrollRect.StopMovement();

            scrollRect.verticalNormalizedPosition =
                0.0f;

            Canvas.ForceUpdateCanvases();

            scrollRect.verticalNormalizedPosition =
                0.0f;
        }


        scrollCoroutine =
            null;
    }


    // =====================================================
    // Immediate Layout Refresh
    // =====================================================

    private void RefreshLayoutImmediate()
    {
        Canvas.ForceUpdateCanvases();

        if (contentRect != null)
        {
            LayoutRebuilder.ForceRebuildLayoutImmediate(
                contentRect
            );
        }

        Canvas.ForceUpdateCanvases();
    }


    // =====================================================
    // Clear
    // =====================================================

    public void Clear()
    {
        lines.Clear();

        if (debugText != null)
        {
            debugText.text = "";

            debugText.ForceMeshUpdate();
        }

        if (scrollCoroutine != null)
        {
            StopCoroutine(
                scrollCoroutine
            );

            scrollCoroutine =
                null;
        }

        StartCoroutine(
            ClearLayoutNextFrame()
        );
    }


    // =====================================================
    // Clear Layout
    // =====================================================

    private IEnumerator ClearLayoutNextFrame()
    {
        Canvas.ForceUpdateCanvases();

        if (contentRect != null)
        {
            LayoutRebuilder.ForceRebuildLayoutImmediate(
                contentRect
            );
        }

        yield return null;

        Canvas.ForceUpdateCanvases();

        if (scrollRect != null)
        {
            scrollRect.StopMovement();

            scrollRect.verticalNormalizedPosition =
                1.0f;
        }
    }


    // =====================================================
    // Auto Scroll
    // =====================================================

    public void SetAutoScroll(bool enabled)
    {
        autoScroll =
            enabled;

        if (
            autoScroll
            &&
            scrollRect != null
        )
        {
            if (scrollCoroutine != null)
            {
                StopCoroutine(
                    scrollCoroutine
                );
            }

            scrollCoroutine =
                StartCoroutine(
                    RefreshAndScrollToBottom()
                );
        }
    }
}