using System;
using System.Net.Sockets;
using System.Text;
using System.Threading.Tasks;
using UnityEngine;


public class Esp32Bridge : MonoBehaviour
{
    // =====================================================
    // Communication
    // =====================================================

    [Header("Communication")]

    [SerializeField]
    private bool communicationEnabled = false;


    // =====================================================
    // Connection
    // =====================================================

    [Header("Connection")]

    [SerializeField]
    private string host = "127.0.0.1";


    [SerializeField]
    private int port = 8181;


    // =====================================================
    // Unity → Arduino
    // =====================================================

    [Header("Input : Unity -> Arduino")]

    [SerializeField]
    private bool sensor01;


    [SerializeField]
    private bool sensor02;


    // =====================================================
    // Arduino → Unity
    // =====================================================

    [Header("Output : Arduino -> Unity")]

    [SerializeField]
    private bool moveLeft;


    [SerializeField]
    private bool moveRight;


    // =====================================================
    // Status
    // =====================================================

    [Header("Status")]

    [SerializeField]
    private bool connected;


    [SerializeField]
    private bool connecting;


    // =====================================================
    // Debug Monitor
    // =====================================================

    [Header("Debug Monitor")]

    [SerializeField]
    private ArduinoDebugMonitor debugMonitor;


    // =====================================================
    // TCP
    // =====================================================

    private TcpClient client;

    private NetworkStream stream;


    // =====================================================
    // Async Connect
    // =====================================================

    private TcpClient connectingClient;

    private Task connectTask;

    private bool isConnecting = false;


    // =====================================================
    // Timer
    // =====================================================

    private float reconnectTimer = 0.0f;

    private float sendTimer = 0.0f;


    private const float RECONNECT_INTERVAL = 1.0f;

    private const float SEND_INTERVAL = 0.02f;


    // =====================================================
    // Receive
    // =====================================================

    private readonly byte[] receiveData =
        new byte[2048];


    private string receiveBuffer = "";


    // =====================================================
    // Public Properties
    // =====================================================

    public bool CommunicationEnabled
    {
        get
        {
            return communicationEnabled;
        }
    }


    public bool IsConnected
    {
        get
        {
            return connected;
        }
    }


    public bool IsConnecting
    {
        get
        {
            return isConnecting;
        }
    }


    public bool Sensor01
    {
        get
        {
            return sensor01;
        }
    }


    public bool Sensor02
    {
        get
        {
            return sensor02;
        }
    }


    public bool MoveLeft
    {
        get
        {
            return moveLeft;
        }
    }


    public bool MoveRight
    {
        get
        {
            return moveRight;
        }
    }


    // =====================================================
    // Unity Sensor → Arduino
    // =====================================================

    public void SetSensor01(
        bool value
    )
    {
        sensor01 =
            value;
    }


    public void SetSensor02(
        bool value
    )
    {
        sensor02 =
            value;
    }


    // =====================================================
    // Communication Enable / Disable
    // =====================================================

    public void SetCommunicationEnabled(
        bool enabled
    )
    {
        communicationEnabled =
            enabled;


        if (!communicationEnabled)
        {
            Disconnect();


            sensor01 =
                false;


            sensor02 =
                false;
        }
        else
        {
            // 다음 Update에서 바로 접속 시도

            reconnectTimer =
                RECONNECT_INTERVAL;
        }
    }


    // =====================================================
    // Start
    // =====================================================

    private void Start()
    {
        if (!communicationEnabled)
        {
            Disconnect();
        }
    }


    // =====================================================
    // Update
    // =====================================================

    private void Update()
    {
        // -------------------------------------------------
        // Arduino 모드가 아니면 통신하지 않는다.
        // -------------------------------------------------

        if (!communicationEnabled)
        {
            return;
        }


        // -------------------------------------------------
        // 연결 안 됨
        // -------------------------------------------------

        if (!connected)
        {
            UpdateReconnect();

            return;
        }


        // -------------------------------------------------
        // 실제 Socket Disconnect 확인
        // -------------------------------------------------

        if (!CheckConnection())
        {
            Disconnect();


            reconnectTimer =
                RECONNECT_INTERVAL;


            return;
        }


        // -------------------------------------------------
        // Unity → ESP32
        // -------------------------------------------------

        SendInputs();


        // -------------------------------------------------
        // ESP32 → Unity
        // -------------------------------------------------

        ReceiveOutputs();


        // -------------------------------------------------
        // 주의
        //
        // 현재 Watchdog은 사용하지 않는다.
        //
        // Wokwi 시뮬레이션 지연을 통신 장애로 오인해서
        // 연결을 반복적으로 끊는 현상이 확인되었기 때문이다.
        // -------------------------------------------------
    }


    // =====================================================
    // Async Reconnect
    // =====================================================

    private void UpdateReconnect()
    {
        // -------------------------------------------------
        // 이미 접속 중
        // -------------------------------------------------

        if (isConnecting)
        {
            CompleteReconnectIfReady();

            return;
        }


        // -------------------------------------------------
        // Reconnect Timer
        // -------------------------------------------------

        reconnectTimer +=
            Time.unscaledDeltaTime;


        if (
            reconnectTimer
            <
            RECONNECT_INTERVAL
        )
        {
            return;
        }


        reconnectTimer =
            0.0f;


        StartReconnectAsync();
    }


    // =====================================================
    // Start Async Connect
    // =====================================================

    private void StartReconnectAsync()
    {
        CancelPendingConnect();


        try
        {
            connectingClient =
                new TcpClient();


            connectingClient.NoDelay =
                true;


            connectTask =
                connectingClient.ConnectAsync(
                    host,
                    port
                );


            isConnecting =
                true;


            connecting =
                true;
        }
        catch
        {
            CancelPendingConnect();


            reconnectTimer =
                0.0f;
        }
    }


    // =====================================================
    // Complete Async Connect
    // =====================================================

    private void CompleteReconnectIfReady()
    {
        if (!isConnecting)
        {
            return;
        }


        if (connectTask == null)
        {
            CancelPendingConnect();

            return;
        }


        // -------------------------------------------------
        // 아직 연결 중
        // -------------------------------------------------

        if (!connectTask.IsCompleted)
        {
            return;
        }


        // -------------------------------------------------
        // 연결 실패
        // -------------------------------------------------

        if (
            connectTask.IsFaulted
            ||
            connectTask.IsCanceled
            ||
            connectingClient == null
            ||
            !connectingClient.Connected
        )
        {
            CancelPendingConnect();


            reconnectTimer =
                0.0f;


            return;
        }


        // -------------------------------------------------
        // 연결 성공
        // -------------------------------------------------

        try
        {
            client =
                connectingClient;


            stream =
                client.GetStream();


            connectingClient =
                null;


            connectTask =
                null;


            isConnecting =
                false;


            connecting =
                false;


            connected =
                true;


            sendTimer =
                0.0f;


            receiveBuffer =
                "";


            Debug.Log(
                "[Arduino] Connected"
            );


            if (debugMonitor != null)
            {
                debugMonitor.AddSystemMessage(
                    "CONNECTED"
                );
            }
        }
        catch (
            Exception exception
        )
        {
            Debug.LogWarning(
                "[Arduino] Connect Error: "
                +
                exception.Message
            );


            Disconnect();


            reconnectTimer =
                0.0f;
        }
    }


    // =====================================================
    // Cancel Pending Connect
    // =====================================================

    private void CancelPendingConnect()
    {
        try
        {
            if (connectingClient != null)
            {
                connectingClient.Close();
            }
        }
        catch
        {
        }


        connectingClient =
            null;


        connectTask =
            null;


        isConnecting =
            false;


        connecting =
            false;
    }


    // =====================================================
    // Connection Check
    // =====================================================

    private bool CheckConnection()
    {
        if (client == null)
        {
            return false;
        }


        if (!client.Connected)
        {
            return false;
        }


        try
        {
            Socket socket =
                client.Client;


            bool disconnected =
                socket.Poll(
                    0,
                    SelectMode.SelectRead
                )
                &&
                socket.Available == 0;


            return !disconnected;
        }
        catch
        {
            return false;
        }
    }


    // =====================================================
    // Unity → ESP32
    //
    // I,Sensor01,Sensor02
    //
    // 예:
    //
    // I,0,0
    // I,1,0
    // I,0,1
    // =====================================================

    private void SendInputs()
    {
        if (stream == null)
        {
            return;
        }


        sendTimer +=
            Time.unscaledDeltaTime;


        if (
            sendTimer
            <
            SEND_INTERVAL
        )
        {
            return;
        }


        sendTimer =
            0.0f;


        string message =
            "I,"
            +
            (sensor01 ? "1" : "0")
            +
            ","
            +
            (sensor02 ? "1" : "0")
            +
            "\n";


        byte[] data =
            Encoding.ASCII.GetBytes(
                message
            );


        try
        {
            stream.Write(
                data,
                0,
                data.Length
            );
        }
        catch (
            Exception exception
        )
        {
            Debug.LogWarning(
                "[Arduino] Send Error: "
                +
                exception.Message
            );


            Disconnect();


            reconnectTimer =
                RECONNECT_INTERVAL;
        }
    }


    // =====================================================
    // ESP32 → Unity Receive
    //
    // Control:
    //
    // O,MoveLeft,MoveRight
    //
    // Debug:
    //
    // #MESSAGE
    // =====================================================

    private void ReceiveOutputs()
    {
        if (stream == null)
        {
            return;
        }


        try
        {
            while (
                stream.DataAvailable
            )
            {
                int count =
                    stream.Read(
                        receiveData,
                        0,
                        receiveData.Length
                    );


                if (count <= 0)
                {
                    Disconnect();


                    reconnectTimer =
                        RECONNECT_INTERVAL;


                    return;
                }


                string received =
                    Encoding.ASCII.GetString(
                        receiveData,
                        0,
                        count
                    );


                receiveBuffer +=
                    received;
            }


            ProcessReceiveBuffer();
        }
        catch (
            Exception exception
        )
        {
            Debug.LogWarning(
                "[Arduino] Receive Error: "
                +
                exception.Message
            );


            Disconnect();


            reconnectTimer =
                RECONNECT_INTERVAL;
        }
    }


    // =====================================================
    // Receive Buffer Processing
    // =====================================================

    private void ProcessReceiveBuffer()
    {
        while (true)
        {
            int newlineIndex =
                receiveBuffer.IndexOf(
                    '\n'
                );


            if (newlineIndex < 0)
            {
                break;
            }


            string packet =
                receiveBuffer.Substring(
                    0,
                    newlineIndex
                );


            receiveBuffer =
                receiveBuffer.Substring(
                    newlineIndex + 1
                );


            // CR만 제거
            //
            // Trim()을 사용하지 않는다.
            // Debug 메시지의 앞뒤 공백을 보존하기 위함.

            packet =
                packet.TrimEnd(
                    '\r'
                );


            ProcessPacket(
                packet
            );
        }
    }


    // =====================================================
    // Packet Processing
    // =====================================================

    private void ProcessPacket(
        string packet
    )
    {
        if (
            string.IsNullOrEmpty(
                packet
            )
        )
        {
            return;
        }


        // -------------------------------------------------
        // Debug Packet
        //
        // #STEP 1 -> STEP 2
        //
        // Unity Console:
        //
        // [ESP32 DEBUG] STEP 1 -> STEP 2
        //
        // Debug Monitor:
        //
        // STEP 1 -> STEP 2
        // -------------------------------------------------

        if (
            packet[0]
            ==
            '#'
        )
        {
            string message =
                packet.Substring(
                    1
                );


            // ---------------------------------------------
            // 중요
            //
            // UI와 상관없이 Unity Console에 무조건 출력한다.
            // ---------------------------------------------

            Debug.Log(
                "[ESP32 DEBUG] "
                +
                message
            );


            // ---------------------------------------------
            // Debug Monitor UI
            // ---------------------------------------------

            if (debugMonitor != null)
            {
                debugMonitor.AddMessage(
                    message
                );
            }
            else
            {
                Debug.LogWarning(
                    "[ESP32 DEBUG] ArduinoDebugMonitor is not assigned."
                );
            }


            return;
        }


        // -------------------------------------------------
        // Control Packet
        //
        // O,0,0
        // O,1,0
        // O,0,1
        // -------------------------------------------------

        string[] values =
            packet.Split(
                ','
            );


        if (values.Length != 3)
        {
            return;
        }


        if (values[0] != "O")
        {
            return;
        }


        moveLeft =
            values[1] == "1";


        moveRight =
            values[2] == "1";
    }


    // =====================================================
    // Disconnect
    // =====================================================

    private void Disconnect()
    {
        bool wasConnected =
            connected;


        connected =
            false;


        connecting =
            false;


        moveLeft =
            false;


        moveRight =
            false;


        sendTimer =
            0.0f;


        receiveBuffer =
            "";


        CancelPendingConnect();


        // -------------------------------------------------
        // Stream
        // -------------------------------------------------

        try
        {
            if (stream != null)
            {
                stream.Close();
            }
        }
        catch
        {
        }


        // -------------------------------------------------
        // Client
        // -------------------------------------------------

        try
        {
            if (client != null)
            {
                client.Close();
            }
        }
        catch
        {
        }


        stream =
            null;


        client =
            null;


        if (wasConnected)
        {
            Debug.Log(
                "[Arduino] Disconnected"
            );


            if (debugMonitor != null)
            {
                debugMonitor.AddSystemMessage(
                    "DISCONNECTED"
                );
            }
        }
    }


    // =====================================================
    // Application End
    // =====================================================

    private void OnDestroy()
    {
        Disconnect();
    }


    private void OnApplicationQuit()
    {
        Disconnect();
    }
}