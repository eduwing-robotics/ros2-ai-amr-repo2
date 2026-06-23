using UnityEngine;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Sensor;
using RosMessageTypes.Nav;
using RosMessageTypes.Std;

public class RosSmokeDashboard : MonoBehaviour
{
    [Header("ROS Connection")]
    public string rosIP = "urhynix-robot.local";
    public int rosPort = 10000;

    // --- ROS topic state ---
    bool scanOk, odomOk, battOk, pirOk, ldrOk;
    int scanCount, odomCount, battCount, pirCount, ldrCount;

    int lastScanRanges;
    string scanFrame = "-";

    double odomX, odomY;
    string odomFrame = "-";

    float battVolt;
    float battPercent;

    bool pirDetected;
    int ldrRaw;

    // --- styling ---
    static Font koreanFont;
    static GUIStyle titleStyle, headerStyle, sectionStyle, dataStyle, valueStyle, bigStyle, smallStyle;
    static Texture2D solidTex;

    void Start()
    {
        var ros = ROSConnection.GetOrCreateInstance();
        ros.RosIPAddress = rosIP;
        ros.RosPort = rosPort;
        ros.Connect();

        ros.Subscribe<LaserScanMsg>("/scan", m =>
        {
            scanOk = true; scanCount++;
            lastScanRanges = m.ranges.Length;
            scanFrame = m.header.frame_id;
        });
        ros.Subscribe<OdometryMsg>("/odom", m =>
        {
            odomOk = true; odomCount++;
            odomX = m.pose.pose.position.x;
            odomY = m.pose.pose.position.y;
            odomFrame = m.header.frame_id;
        });
        ros.Subscribe<BatteryStateMsg>("/battery_state", m =>
        {
            battOk = true; battCount++;
            battVolt = m.voltage;
            battPercent = m.percentage * 100f;
        });
        ros.Subscribe<BoolMsg>("/sensors/pir", m =>
        {
            pirOk = true; pirCount++;
            pirDetected = m.data;
        });
        ros.Subscribe<Int32Msg>("/sensors/ldr", m =>
        {
            ldrOk = true; ldrCount++;
            ldrRaw = m.data;
        });

        Debug.Log($"[RosSmoke] Connecting to {rosIP}:{rosPort}");
    }

    static void EnsureStyles()
    {
        if (koreanFont == null)
        {
            string[] fonts = { "Apple SD Gothic Neo", "AppleGothic", "Malgun Gothic",
                               "Noto Sans CJK KR", "Noto Sans KR", "NanumGothic", "DejaVu Sans" };
            koreanFont = Font.CreateDynamicFontFromOSFont(fonts, 20);
        }
        if (solidTex == null)
        {
            solidTex = new Texture2D(1, 1); solidTex.SetPixel(0, 0, Color.white); solidTex.Apply();
            solidTex.hideFlags = HideFlags.HideAndDontSave;
        }
        if (titleStyle == null)
        {
            titleStyle = new GUIStyle { font = koreanFont, fontSize = 30, fontStyle = FontStyle.Bold,
                alignment = TextAnchor.MiddleCenter, normal = { textColor = Color.white } };
            headerStyle = new GUIStyle { font = koreanFont, fontSize = 22, fontStyle = FontStyle.Bold,
                alignment = TextAnchor.MiddleCenter };
            sectionStyle = new GUIStyle { font = koreanFont, fontSize = 18, fontStyle = FontStyle.Bold,
                alignment = TextAnchor.MiddleLeft, normal = { textColor = new Color(0.6f, 0.85f, 1f) } };
            dataStyle = new GUIStyle { font = koreanFont, fontSize = 20,
                alignment = TextAnchor.MiddleLeft, normal = { textColor = Color.white } };
            valueStyle = new GUIStyle { font = koreanFont, fontSize = 20,
                alignment = TextAnchor.MiddleLeft, normal = { textColor = new Color(1f, 1f, 0.85f) } };
            bigStyle = new GUIStyle { font = koreanFont, fontSize = 44, fontStyle = FontStyle.Bold,
                alignment = TextAnchor.MiddleCenter };
            smallStyle = new GUIStyle { font = koreanFont, fontSize = 14,
                alignment = TextAnchor.MiddleRight, normal = { textColor = new Color(0.7f, 0.7f, 0.7f) } };
        }
    }

    static string LdrLabel(int v)
    {
        if (v < 200) return "어두움";
        if (v < 600) return "약간 어두움";
        if (v < 900) return "밝음";
        return "매우 밝음";
    }

    void OnGUI()
    {
        EnsureStyles();

        const int W = 780;
        const int H = 600;
        int x = (Screen.width - W) / 2;
        int y = (Screen.height - H) / 2;

        // 배경 (반투명 검정 + 파랑 테두리)
        DrawFill(x, y, W, H, new Color(0.04f, 0.06f, 0.10f, 0.88f));
        DrawBorder(x, y, W, H, 2, new Color(0.30f, 0.65f, 1f, 1f));

        int innerX = x + 24;
        int curY = y + 18;
        int innerW = W - 48;

        // 타이틀
        GUI.Label(new Rect(innerX, curY, innerW, 38),
            "URHYNIX 디지털트윈경비로봇 · 라이브 모니터", titleStyle);
        curY += 48;

        // 연결 상태
        bool connected = !ROSConnection.GetOrCreateInstance().HasConnectionError;
        Color connColor = connected ? new Color(0.3f, 1f, 0.4f) : new Color(1f, 0.35f, 0.35f);
        headerStyle.normal.textColor = connColor;
        GUI.Label(new Rect(innerX, curY, innerW, 30),
            (connected ? "● ROS-TCP 연결됨" : "○ ROS-TCP 끊김") + $"   ({rosIP}:{rosPort})", headerStyle);
        curY += 42;

        // 섹션: 터틀봇
        GUI.Label(new Rect(innerX, curY, innerW, 24), "▍ 터틀봇 토픽", sectionStyle);
        curY += 30;
        DrawRow(innerX, curY, innerW, "레이저 (/scan)", scanOk, scanCount,
            $"포인트 {lastScanRanges}개   ·   프레임 {scanFrame}");
        curY += 36;
        DrawRow(innerX, curY, innerW, "오도메트리 (/odom)", odomOk, odomCount,
            $"x = {odomX:F2} m   y = {odomY:F2} m   ·   프레임 {odomFrame}");
        curY += 36;
        DrawRow(innerX, curY, innerW, "배터리 (/battery_state)", battOk, battCount,
            $"{battVolt:F2} V   ({battPercent:F0} %)");
        curY += 46;

        // 섹션: 아두이노
        GUI.Label(new Rect(innerX, curY, innerW, 24), "▍ 아두이노 센서", sectionStyle);
        curY += 30;

        // PIR — 감지 시 주황 강조
        bool pirAlarm = pirOk && pirDetected;
        Color pirColor = pirAlarm ? new Color(1f, 0.7f, 0.2f)
                                  : (pirOk ? new Color(0.3f, 1f, 0.4f) : Color.gray);
        DrawRowColored(innerX, curY, innerW, "인체감지 (/sensors/pir)", pirOk, pirCount,
            pirOk ? (pirDetected ? "⚠ 감지됨 (MOTION)" : "없음 (CLEAR)") : "-", pirColor);
        curY += 36;

        // LDR
        DrawRow(innerX, curY, innerW, "조도 (/sensors/ldr)", ldrOk, ldrCount,
            ldrOk ? $"A0 = {ldrRaw}   ·   {LdrLabel(ldrRaw)}" : "-");
        curY += 50;

        // 종합 상태
        bool liveAll = scanOk && odomOk && battOk && pirOk && ldrOk;
        bool liveCore = scanOk && odomOk && battOk;
        string state;
        Color stateColor;
        if (liveAll)        { state = "● 전체 LIVE";              stateColor = new Color(0.3f, 1f, 0.4f); }
        else if (liveCore)  { state = "◐ 부분 LIVE (아두이노 대기)"; stateColor = new Color(1f, 0.9f, 0.3f); }
        else                { state = "○ 연결 대기 중";              stateColor = new Color(1f, 0.6f, 0.2f); }
        bigStyle.normal.textColor = stateColor;
        GUI.Label(new Rect(innerX, curY, innerW, 60), state, bigStyle);
    }

    // 흰색
    static void DrawRow(int x, int y, int w, string label, bool ok, int count, string value)
    {
        DrawRowColored(x, y, w, label, ok, count, value, ok ? Color.white : new Color(0.6f, 0.6f, 0.6f));
    }

    static void DrawRowColored(int x, int y, int w, string label, bool ok, int count, string value, Color valueColor)
    {
        EnsureStyles();
        dataStyle.normal.textColor = ok ? Color.white : new Color(0.6f, 0.6f, 0.6f);
        valueStyle.normal.textColor = valueColor;

        string status = ok ? "✓" : "·";
        GUI.Label(new Rect(x, y, 280, 32), $"  {status}  {label}", dataStyle);
        GUI.Label(new Rect(x + 290, y, w - 290 - 70, 32), value, valueStyle);
        GUI.Label(new Rect(x + w - 70, y, 70, 32), ok ? $"#{count}" : "", smallStyle);
    }

    static void DrawFill(int x, int y, int w, int h, Color c)
    {
        var prev = GUI.color; GUI.color = c;
        GUI.DrawTexture(new Rect(x, y, w, h), solidTex);
        GUI.color = prev;
    }

    static void DrawBorder(int x, int y, int w, int h, int t, Color c)
    {
        var prev = GUI.color; GUI.color = c;
        GUI.DrawTexture(new Rect(x, y, w, t), solidTex);
        GUI.DrawTexture(new Rect(x, y + h - t, w, t), solidTex);
        GUI.DrawTexture(new Rect(x, y, t, h), solidTex);
        GUI.DrawTexture(new Rect(x + w - t, y, t, h), solidTex);
        GUI.color = prev;
    }
}
