// CameraStreamPanel.cs — 카메라 라이브 RGB 패널 (확장성 설계)
// URHYNIX 박물관 시연 — 티원/젠지 카메라 동시 표시 가능
//
// 사용 방법:
//   1. Canvas 안에 GameObject 생성 (이름: "GenjiCameraPanel" 또는 "T1CameraPanel")
//   2. RawImage 컴포넌트 추가
//   3. 이 스크립트 컴포넌트 추가
//   4. Inspector에서 topicName + displayLabel 설정
//      - 젠지 (tb3_2 / Pi Camera v2 IMX219):
//          topicName = "/tb3_2/camera/image_raw/compressed"
//          displayLabel = "젠지"
//      - 티원 (tb3_1 / RealSense D435):
//          topicName = "/tb3_1/camera/camera/color/image_raw/compressed"
//          displayLabel = "티원"
//   5. Play → 라이브 영상 표시
//
// 카메라 추가 = GameObject 복제 + Inspector에서 topicName/displayLabel 한 줄 변경.
//
// 의존:
//   - ROS-TCP-Connector (unity-smoke에 이미 설치)
//   - RosMessageTypes.Sensor.CompressedImageMsg
//   - Robot 측에서 해당 topic 발행 중 (ros-jazzy-camera-ros 또는 realsense2_camera)
using UnityEngine;
using UnityEngine.UI;
using Unity.Robotics.ROSTCPConnector;
using RosMessageTypes.Sensor;

public class CameraStreamPanel : MonoBehaviour
{
    [Header("ROS Topic (Inspector에서 변경)")]
    [Tooltip("예: /tb3_2/camera/image_raw/compressed (젠지) / /tb3_1/camera/camera/color/image_raw/compressed (티원)")]
    public string topicName = "/tb3_2/camera/image_raw/compressed";

    [Header("Display")]
    [Tooltip("패널 라벨에 표시할 이름. 예: '젠지' 또는 '티원'")]
    public string displayLabel = "젠지";

    [Tooltip("RGB 영상이 그려질 RawImage (비워두면 같은 GameObject의 RawImage 자동 사용)")]
    public RawImage targetImage;

    [Tooltip("라벨 + hz 표시할 Text (옵션)")]
    public Text labelText;

    // --- internal ---
    Texture2D streamTexture;
    int frameCount;
    float lastHzCheck;
    float currentHz;
    bool subscribed;

    void Start()
    {
        if (targetImage == null)
            targetImage = GetComponent<RawImage>();

        if (targetImage == null)
        {
            Debug.LogError($"[CameraStreamPanel:{displayLabel}] RawImage 컴포넌트 없음. Inspector에서 targetImage 지정하거나 같은 GameObject에 RawImage 추가하세요.");
            enabled = false;
            return;
        }

        streamTexture = new Texture2D(2, 2, TextureFormat.RGB24, false);
        targetImage.texture = streamTexture;

        var ros = ROSConnection.GetOrCreateInstance();
        ros.Subscribe<CompressedImageMsg>(topicName, OnImageReceived);
        subscribed = true;

        if (labelText != null) labelText.text = displayLabel;
        lastHzCheck = Time.time;

        Debug.Log($"[CameraStreamPanel:{displayLabel}] subscribed → {topicName}");
    }

    void OnImageReceived(CompressedImageMsg msg)
    {
        // JPEG/PNG bytes → Texture2D 자동 decode
        if (streamTexture.LoadImage(msg.data))
        {
            frameCount++;
        }
    }

    void Update()
    {
        if (!subscribed) return;

        float dt = Time.time - lastHzCheck;
        if (dt >= 1.0f)
        {
            currentHz = frameCount / dt;
            frameCount = 0;
            lastHzCheck = Time.time;

            if (labelText != null)
                labelText.text = $"{displayLabel} ({currentHz:F1} Hz)";
        }
    }

    void OnDestroy()
    {
        if (streamTexture != null) Destroy(streamTexture);
    }
}
