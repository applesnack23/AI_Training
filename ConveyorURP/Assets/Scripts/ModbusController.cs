using System;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;
using TMPro;

public class ModbusController : MonoBehaviour
{
    // =========================================================
    // Modbus TCP 설정
    // =========================================================

    [Header("Modbus TCP")]
    [SerializeField] private string ipAddress = "127.0.0.1";
    [SerializeField] private int port = 1502;
    [SerializeField] private byte unitId = 1;


    // =========================================================
    // Modbus UI
    // =========================================================

    [Header("Modbus UI")]
    [SerializeField] private TMP_InputField ipInputField;


    // =========================================================
    // Register Address
    // =========================================================

    [Header("Register Address")]
    [SerializeField] private ushort writeStartAddress = 0;
    [SerializeField] private ushort readStartAddress = 10;


    // =========================================================
    // Communication Timing
    // =========================================================

    [Header("Communication Timing")]
    [SerializeField] private int pollIntervalMs = 20;
    [SerializeField] private int reconnectIntervalMs = 1000;
    [SerializeField] private int connectTimeoutMs = 500;
    [SerializeField] private int responseTimeoutMs = 500;


    // =========================================================
    // Modbus Data
    // =========================================================

    // Unity → Controller
    public ushort[] toController = new ushort[10];

    // Controller → Unity
    public ushort[] fromController = new ushort[10];


    // =========================================================
    // Connection State
    // =========================================================

    [Header("Connection State")]
    [SerializeField] private bool bIsConnected = false;


    public bool IsConnected
    {
        get
        {
            return bIsConnected;
        }
    }


    // =========================================================
    // Communication Enable
    // =========================================================

    [Header("Communication Enable")]
    [SerializeField] private bool communicationEnabled = false;


    public bool CommunicationEnabled
    {
        get
        {
            return communicationEnabled;
        }
    }


    // =========================================================
    // Internal
    // =========================================================

    private TcpClient tcpClient;
    private NetworkStream networkStream;

    private CancellationTokenSource cancellationTokenSource;
    private Task communicationTask;

    private ushort transactionId = 0;


    // =========================================================
    // Unity Start
    // =========================================================

    private void Start()
    {
        // -----------------------------------------------------
        // InputField 초기화
        // -----------------------------------------------------

        if (ipInputField != null)
        {
            ipInputField.text =
                ipAddress;

            // 입력 완료 시 IP 주소 적용
            ipInputField.onEndEdit.AddListener(
                OnIpAddressChanged
            );
        }


        // -----------------------------------------------------
        // Communication Task 시작
        // -----------------------------------------------------

        cancellationTokenSource =
            new CancellationTokenSource();


        communicationTask =
            Task.Run(
                () =>
                    CommunicationLoopAsync(
                        cancellationTokenSource.Token
                    )
            );
    }


    // =========================================================
    // Unity Destroy
    // =========================================================

    private void OnDestroy()
    {
        if (ipInputField != null)
        {
            ipInputField.onEndEdit.RemoveListener(
                OnIpAddressChanged
            );
        }


        StopCommunication();
    }


    private void OnApplicationQuit()
    {
        StopCommunication();
    }


    // =========================================================
    // IP Address 변경
    // =========================================================

    private void OnIpAddressChanged(
        string value
    )
    {
        string input =
            value.Trim();


        // -----------------------------------------------------
        // 빈 문자열 검사
        // -----------------------------------------------------

        if (string.IsNullOrWhiteSpace(input))
        {
            Debug.LogWarning(
                "[MODBUS] IP Address is empty."
            );


            if (ipInputField != null)
            {
                ipInputField.text =
                    ipAddress;
            }


            return;
        }


        // -----------------------------------------------------
        // IP 형식 검사
        // -----------------------------------------------------

        if (!IPAddress.TryParse(
                input,
                out _
            ))
        {
            Debug.LogWarning(
                $"[MODBUS] Invalid IP Address : {input}"
            );


            // 기존 IP로 복구
            if (ipInputField != null)
            {
                ipInputField.text =
                    ipAddress;
            }


            return;
        }


        // -----------------------------------------------------
        // 기존 IP와 같은 경우
        // -----------------------------------------------------

        if (ipAddress == input)
        {
            return;
        }


        // -----------------------------------------------------
        // IP 변경
        // -----------------------------------------------------

        ipAddress =
            input;


        Debug.Log(
            $"[MODBUS] IP Changed : {ipAddress}:{port}"
        );


        // -----------------------------------------------------
        // 현재 통신 중이면 재접속
        // -----------------------------------------------------

        if (communicationEnabled)
        {
            Disconnect();


            Debug.Log(
                $"[MODBUS] Reconnecting : {ipAddress}:{port}"
            );
        }
    }


    // =========================================================
    // InputField에서 IP 주소 읽기
    // =========================================================

    private bool ApplyIpAddressFromInput()
    {
        // InputField가 없으면
        // Inspector의 ipAddress 사용

        if (ipInputField == null)
        {
            return true;
        }


        string input =
            ipInputField.text.Trim();


        // -----------------------------------------------------
        // 빈 문자열 검사
        // -----------------------------------------------------

        if (string.IsNullOrWhiteSpace(input))
        {
            Debug.LogWarning(
                "[MODBUS] IP Address is empty."
            );


            return false;
        }


        // -----------------------------------------------------
        // IP 형식 검사
        // -----------------------------------------------------

        if (!IPAddress.TryParse(
                input,
                out _
            ))
        {
            Debug.LogWarning(
                $"[MODBUS] Invalid IP Address : {input}"
            );


            return false;
        }


        // -----------------------------------------------------
        // IP 적용
        // -----------------------------------------------------

        ipAddress =
            input;


        Debug.Log(
            $"[MODBUS] IP Applied : {ipAddress}:{port}"
        );


        return true;
    }


    // =========================================================
    // 외부에서 IP 설정
    // =========================================================

    public void SetIpAddress(
        string value
    )
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return;
        }


        string input =
            value.Trim();


        if (!IPAddress.TryParse(
                input,
                out _
            ))
        {
            Debug.LogWarning(
                $"[MODBUS] Invalid IP Address : {input}"
            );


            return;
        }


        // -----------------------------------------------------
        // 같은 IP
        // -----------------------------------------------------

        if (ipAddress == input)
        {
            return;
        }


        ipAddress =
            input;


        if (ipInputField != null)
        {
            ipInputField.text =
                ipAddress;
        }


        Debug.Log(
            $"[MODBUS] IP Set : {ipAddress}:{port}"
        );


        // -----------------------------------------------------
        // 통신 중이면 재접속
        // -----------------------------------------------------

        if (communicationEnabled)
        {
            Disconnect();
        }
    }


    // =========================================================
    // Communication Enable / Disable
    // =========================================================

    public void SetCommunicationEnabled(
        bool enabled
    )
    {
        // =====================================================
        // 통신 활성화
        // =====================================================

        if (enabled)
        {
            // -------------------------------------------------
            // UI에서 현재 IP 읽기
            // -------------------------------------------------

            if (!ApplyIpAddressFromInput())
            {
                return;
            }


            // -------------------------------------------------
            // 이미 통신 활성 상태
            //
            // Controller 버튼을 다시 누르면
            // 현재 IP로 재접속
            // -------------------------------------------------

            if (communicationEnabled)
            {
                Disconnect();


                Debug.Log(
                    $"[MODBUS] Reconnect : {ipAddress}:{port}"
                );


                return;
            }


            communicationEnabled =
                true;


            Debug.Log(
                $"[MODBUS] Communication Enabled : {ipAddress}:{port}"
            );


            return;
        }


        // =====================================================
        // 통신 비활성화
        // =====================================================

        if (!communicationEnabled)
        {
            return;
        }


        communicationEnabled =
            false;


        Debug.Log(
            "[MODBUS] Communication Disabled"
        );


        // -----------------------------------------------------
        // Controller → Unity 데이터 초기화
        // -----------------------------------------------------

        Array.Clear(
            fromController,
            0,
            fromController.Length
        );


        // -----------------------------------------------------
        // TCP 연결 종료
        // -----------------------------------------------------

        Disconnect();
    }


    // =========================================================
    // Main Communication Loop
    // =========================================================

    private async Task CommunicationLoopAsync(
        CancellationToken token
    )
    {
        while (!token.IsCancellationRequested)
        {
            // =================================================
            // Controller 모드가 아닌 경우
            // =================================================

            if (!communicationEnabled)
            {
                if (bIsConnected)
                {
                    Disconnect();
                }


                await DelaySafe(
                    100,
                    token
                );


                continue;
            }


            // =================================================
            // 연결되지 않은 상태
            // =================================================

            if (!bIsConnected)
            {
                bool connected =
                    await TryConnectAsync(
                        token
                    );


                if (!connected)
                {
                    await DelaySafe(
                        reconnectIntervalMs,
                        token
                    );


                    continue;
                }
            }


            // =================================================
            // 연결된 상태
            // =================================================

            try
            {
                // ---------------------------------------------
                // 통신 모드 재확인
                // ---------------------------------------------

                if (!communicationEnabled)
                {
                    Disconnect();

                    continue;
                }


                // ---------------------------------------------
                // Unity → Controller 데이터 복사
                // ---------------------------------------------

                ushort[] writeData =
                    new ushort[10];


                Array.Copy(
                    toController,
                    writeData,
                    10
                );


                // ---------------------------------------------
                // FC23
                // Write + Read Multiple Registers
                // ---------------------------------------------

                ushort[] readData =
                    await ReadWriteMultipleRegistersAsync(
                        readStartAddress,
                        10,
                        writeStartAddress,
                        writeData,
                        token
                    );


                // ---------------------------------------------
                // 응답 검증
                // ---------------------------------------------

                if (
                    readData == null ||
                    readData.Length != 10
                )
                {
                    throw new Exception(
                        "Invalid Modbus response."
                    );
                }


                // ---------------------------------------------
                // Controller → Unity 데이터 복사
                // ---------------------------------------------

                Array.Copy(
                    readData,
                    fromController,
                    10
                );


                // ---------------------------------------------
                // 다음 Polling까지 대기
                // ---------------------------------------------

                await DelaySafe(
                    pollIntervalMs,
                    token
                );
            }
            catch (OperationCanceledException)
            {
                if (token.IsCancellationRequested)
                {
                    break;
                }


                Disconnect();
            }
            catch (Exception ex)
            {
                Debug.LogWarning(
                    $"[MODBUS] Communication Error : {ex.Message}"
                );


                Disconnect();
            }
        }


        Disconnect();
    }


    // =========================================================
    // Connect
    // =========================================================

    private async Task<bool> TryConnectAsync(
        CancellationToken token
    )
    {
        if (!communicationEnabled)
        {
            return false;
        }


        try
        {
            Disconnect();


            if (!communicationEnabled)
            {
                return false;
            }


            TcpClient newClient =
                new TcpClient();


            newClient.NoDelay =
                true;


            // -------------------------------------------------
            // Connection Log
            // -------------------------------------------------

            Debug.Log(
                $"[MODBUS] Connecting : {ipAddress}:{port}"
            );


            // -------------------------------------------------
            // TCP Connect
            // -------------------------------------------------

            Task connectTask =
                newClient.ConnectAsync(
                    ipAddress,
                    port
                );


            Task timeoutTask =
                Task.Delay(
                    connectTimeoutMs,
                    token
                );


            Task completedTask =
                await Task.WhenAny(
                    connectTask,
                    timeoutTask
                );


            // -------------------------------------------------
            // Timeout
            // -------------------------------------------------

            if (completedTask != connectTask)
            {
                newClient.Close();


                bIsConnected =
                    false;


                Debug.LogWarning(
                    $"[MODBUS] Connection Timeout : {ipAddress}:{port}"
                );


                return false;
            }


            await connectTask;


            // -------------------------------------------------
            // 연결 상태 확인
            // -------------------------------------------------

            if (!newClient.Connected)
            {
                newClient.Close();


                bIsConnected =
                    false;


                return false;
            }


            // -------------------------------------------------
            // 연결 중 모드 변경 확인
            // -------------------------------------------------

            if (!communicationEnabled)
            {
                newClient.Close();


                bIsConnected =
                    false;


                return false;
            }


            // -------------------------------------------------
            // Client 적용
            // -------------------------------------------------

            tcpClient =
                newClient;


            networkStream =
                tcpClient.GetStream();


            bIsConnected =
                true;


            Debug.Log(
                $"[MODBUS] Connected : {ipAddress}:{port}"
            );


            return true;
        }
        catch (Exception ex)
        {
            Debug.LogWarning(
                $"[MODBUS] Connection Failed : {ipAddress}:{port} / {ex.Message}"
            );


            Disconnect();


            return false;
        }
    }


    // =========================================================
    // Disconnect
    // =========================================================

    private void Disconnect()
    {
        bool wasConnected =
            bIsConnected;


        bIsConnected =
            false;


        // -----------------------------------------------------
        // NetworkStream Close
        // -----------------------------------------------------

        try
        {
            networkStream?.Close();
        }
        catch
        {
        }


        // -----------------------------------------------------
        // TcpClient Close
        // -----------------------------------------------------

        try
        {
            tcpClient?.Close();
        }
        catch
        {
        }


        networkStream =
            null;


        tcpClient =
            null;


        if (wasConnected)
        {
            Debug.Log(
                "[MODBUS] Disconnected"
            );
        }
    }


    // =========================================================
    // FC23
    // Read / Write Multiple Registers
    // =========================================================

    private async Task<ushort[]> ReadWriteMultipleRegistersAsync(
        ushort readAddress,
        ushort readCount,
        ushort writeAddress,
        ushort[] writeData,
        CancellationToken token
    )
    {
        if (networkStream == null)
        {
            throw new Exception(
                "Network stream is null."
            );
        }


        ushort writeCount =
            (ushort)writeData.Length;


        // =====================================================
        // Transaction ID
        // =====================================================

        transactionId++;


        ushort currentTransactionId =
            transactionId;


        // =====================================================
        // FC23 PDU
        //
        // Function               1
        // Read Start Address     2
        // Read Quantity          2
        // Write Start Address    2
        // Write Quantity         2
        // Byte Count             1
        // Write Data             N * 2
        //
        // = 10 + N * 2
        // =====================================================

        int pduLength =
            10 + (writeCount * 2);


        // =====================================================
        // MBAP Length
        //
        // Unit ID + PDU
        // =====================================================

        ushort mbapLength =
            (ushort)(
                1 + pduLength
            );


        byte[] request =
            new byte[
                6 + mbapLength
            ];


        // =====================================================
        // MBAP Header
        // =====================================================

        // Transaction ID

        WriteUInt16(
            request,
            0,
            currentTransactionId
        );


        // Protocol ID = 0

        WriteUInt16(
            request,
            2,
            0
        );


        // Length

        WriteUInt16(
            request,
            4,
            mbapLength
        );


        // Unit ID

        request[6] =
            unitId;


        // =====================================================
        // Function Code
        // =====================================================

        request[7] =
            0x17;


        // =====================================================
        // Read Address
        // =====================================================

        WriteUInt16(
            request,
            8,
            readAddress
        );


        // Read Quantity

        WriteUInt16(
            request,
            10,
            readCount
        );


        // =====================================================
        // Write Address
        // =====================================================

        WriteUInt16(
            request,
            12,
            writeAddress
        );


        // Write Quantity

        WriteUInt16(
            request,
            14,
            writeCount
        );


        // =====================================================
        // Byte Count
        // =====================================================

        request[16] =
            (byte)(
                writeCount * 2
            );


        // =====================================================
        // Register Data
        // =====================================================

        int offset =
            17;


        for (
            int i = 0;
            i < writeCount;
            i++
        )
        {
            WriteUInt16(
                request,
                offset,
                writeData[i]
            );


            offset +=
                2;
        }


        // =====================================================
        // Timeout
        // =====================================================

        using CancellationTokenSource timeout =
            CancellationTokenSource
                .CreateLinkedTokenSource(
                    token
                );


        timeout.CancelAfter(
            responseTimeoutMs
        );


        // =====================================================
        // Send
        // =====================================================

        await networkStream.WriteAsync(
            request,
            0,
            request.Length,
            timeout.Token
        );


        await networkStream.FlushAsync(
            timeout.Token
        );


        // =====================================================
        // Receive MBAP Header
        // =====================================================

        byte[] header =
            new byte[7];


        await ReadExactAsync(
            networkStream,
            header,
            0,
            7,
            timeout.Token
        );


        // =====================================================
        // Header Data
        // =====================================================

        ushort responseTransactionId =
            ReadUInt16(
                header,
                0
            );


        ushort protocolId =
            ReadUInt16(
                header,
                2
            );


        ushort responseLength =
            ReadUInt16(
                header,
                4
            );


        byte responseUnitId =
            header[6];


        // =====================================================
        // Header Validation
        // =====================================================

        if (
            responseTransactionId !=
            currentTransactionId
        )
        {
            throw new Exception(
                "Transaction ID mismatch."
            );
        }


        if (protocolId != 0)
        {
            throw new Exception(
                "Invalid Modbus protocol ID."
            );
        }


        if (
            responseUnitId !=
            unitId
        )
        {
            throw new Exception(
                "Unit ID mismatch."
            );
        }


        // =====================================================
        // responseLength에는 Unit ID 포함
        // 이미 Unit ID 1 Byte를 읽었으므로 -1
        // =====================================================

        int remainingLength =
            responseLength - 1;


        if (remainingLength <= 0)
        {
            throw new Exception(
                "Invalid Modbus response length."
            );
        }


        byte[] response =
            new byte[
                remainingLength
            ];


        await ReadExactAsync(
            networkStream,
            response,
            0,
            remainingLength,
            timeout.Token
        );


        // =====================================================
        // Modbus Exception
        // =====================================================

        if (
            response.Length > 0 &&
            response[0] == 0x97
        )
        {
            byte exceptionCode =
                response.Length > 1
                    ? response[1]
                    : (byte)0;


            throw new Exception(
                $"Modbus Exception: {exceptionCode}"
            );
        }


        // =====================================================
        // 최소 길이 확인
        // =====================================================

        if (response.Length < 2)
        {
            throw new Exception(
                "Invalid Modbus response."
            );
        }


        // =====================================================
        // FC23 확인
        // =====================================================

        if (response[0] != 0x17)
        {
            throw new Exception(
                "Invalid Modbus function code."
            );
        }


        // =====================================================
        // Byte Count
        // =====================================================

        byte byteCount =
            response[1];


        if (
            byteCount !=
            readCount * 2
        )
        {
            throw new Exception(
                "Invalid Modbus byte count."
            );
        }


        // =====================================================
        // 응답 데이터 길이 확인
        // =====================================================

        if (
            response.Length <
            2 + byteCount
        )
        {
            throw new Exception(
                "Invalid Modbus register data length."
            );
        }


        // =====================================================
        // Register 변환
        // =====================================================

        ushort[] result =
            new ushort[
                readCount
            ];


        offset =
            2;


        for (
            int i = 0;
            i < readCount;
            i++
        )
        {
            result[i] =
                ReadUInt16(
                    response,
                    offset
                );


            offset +=
                2;
        }


        return result;
    }


    // =========================================================
    // Read Exact Bytes
    // =========================================================

    private async Task ReadExactAsync(
        NetworkStream stream,
        byte[] buffer,
        int offset,
        int count,
        CancellationToken token
    )
    {
        int totalRead =
            0;


        while (totalRead < count)
        {
            int read =
                await stream.ReadAsync(
                    buffer,
                    offset + totalRead,
                    count - totalRead,
                    token
                );


            if (read == 0)
            {
                throw new Exception(
                    "Modbus TCP connection closed."
                );
            }


            totalRead +=
                read;
        }
    }


    // =========================================================
    // UInt16 Big Endian
    // =========================================================

    private void WriteUInt16(
        byte[] buffer,
        int offset,
        ushort value
    )
    {
        buffer[offset] =
            (byte)(
                value >> 8
            );


        buffer[offset + 1] =
            (byte)(
                value & 0xFF
            );
    }


    private ushort ReadUInt16(
        byte[] buffer,
        int offset
    )
    {
        return (ushort)(
            (buffer[offset] << 8)
            |
            buffer[offset + 1]
        );
    }


    // =========================================================
    // Delay
    // =========================================================

    private async Task DelaySafe(
        int milliseconds,
        CancellationToken token
    )
    {
        try
        {
            await Task.Delay(
                milliseconds,
                token
            );
        }
        catch (OperationCanceledException)
        {
        }
    }


    // =========================================================
    // Stop
    // =========================================================

    private void StopCommunication()
    {
        try
        {
            cancellationTokenSource?.Cancel();
        }
        catch
        {
        }


        Disconnect();
    }


    // =========================================================
    // Bit Helper
    // =========================================================

    public bool GetFromControllerBit(
        int wordIndex,
        int bitIndex
    )
    {
        // -----------------------------------------------------
        // 범위 검사
        // -----------------------------------------------------

        if (
            wordIndex < 0 ||
            wordIndex >= fromController.Length
        )
        {
            return false;
        }


        if (
            bitIndex < 0 ||
            bitIndex > 15
        )
        {
            return false;
        }


        ushort mask =
            (ushort)(
                1 << bitIndex
            );


        return (
            fromController[wordIndex] & mask
        ) != 0;
    }


    public void SetToControllerBit(
        int wordIndex,
        int bitIndex,
        bool value
    )
    {
        // -----------------------------------------------------
        // 범위 검사
        // -----------------------------------------------------

        if (
            wordIndex < 0 ||
            wordIndex >= toController.Length
        )
        {
            return;
        }


        if (
            bitIndex < 0 ||
            bitIndex > 15
        )
        {
            return;
        }


        ushort mask =
            (ushort)(
                1 << bitIndex
            );


        if (value)
        {
            toController[wordIndex] |=
                mask;
        }
        else
        {
            toController[wordIndex] &=
                (ushort)~mask;
        }
    }
}