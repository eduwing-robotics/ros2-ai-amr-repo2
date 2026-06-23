# RealSense D435 Windows pyrealsense2 smoke (2026-06-01)

> Windows workstation에서 Intel RealSense D435가 OS 장치 인식뿐 아니라 `pyrealsense2` streaming pipeline까지 정상 통과한 증거. 기존 Mac evidence의 "macOS streaming blocked" 결론은 macOS Tahoe + brew librealsense 한정 이슈로 유지하고, Windows에서는 RGB-D frame 수신이 가능함을 별도 확인했다.

## Environment

| Item | Value |
|---|---|
| Host | Windows workstation in Codex desktop workspace |
| Repository | `C:\UR\URHYNIX` |
| Test date | 2026-06-01 |
| Python used for smoke | Codex bundled Python 3.12 venv |
| Package | `pyrealsense2==2.58.1.10581` |
| Camera | Intel RealSense D435 |

## Windows device recognition

Command:

```powershell
Get-CimInstance Win32_PnPEntity |
  Where-Object {
    $_.Name -match 'RealSense|Intel.*Camera|D435|Depth' -or
    $_.DeviceID -match 'VID_8086|0B07|0B3A'
  } |
  Select-Object Status,PNPClass,Name,DeviceID
```

Result:

```text
Status : OK
Class  : Camera
Name   : Intel(R) RealSense(TM) Depth Camera 435 with RGB Module RGB
ID     : USB\VID_8086&PID_0B07&MI_03\6&15AB29A4&0&0003

Status : OK
Class  : Camera
Name   : Intel(R) RealSense(TM) Depth Camera 435 with RGB Module Depth
ID     : USB\VID_8086&PID_0B07&MI_00\6&15AB29A4&0&0000

Status : OK
Class  : USB
Name   : USB Composite Device
ID     : USB\VID_8086&PID_0B07\350423023342
```

Verdict: PASS. Windows sees the D435 RGB module, depth module, and composite USB device.

## pyrealsense2 streaming smoke

Test script:

```python
import pyrealsense2 as rs

ctx = rs.context()
devs = ctx.query_devices()
print("devices", len(devs))

for dev in devs:
    print("name", dev.get_info(rs.camera_info.name))
    print("serial", dev.get_info(rs.camera_info.serial_number))
    print("product_id", dev.get_info(rs.camera_info.product_id))
    print("fw", dev.get_info(rs.camera_info.firmware_version))

pipeline = rs.pipeline()
cfg = rs.config()
cfg.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
cfg.enable_stream(rs.stream.color, 640, 480, rs.format.rgb8, 30)

pipeline.start(cfg)
try:
    frames = None
    for _ in range(30):
        frames = pipeline.wait_for_frames(5000)

    depth = frames.get_depth_frame()
    color = frames.get_color_frame()
    print("frames depth", depth.get_width(), depth.get_height(),
          "color", color.get_width(), color.get_height())
    print("center_distance_m",
          round(depth.get_distance(depth.get_width() // 2, depth.get_height() // 2), 4))
finally:
    pipeline.stop()
```

Observed output:

```text
devices 1
name Intel RealSense D435
serial 254522075185
product_id 0B07
fw 5.17.0.10
pipeline started
frames depth 640 480 color 640 480
center_distance_m 0.159
pipeline stopped
```

Verdict: PASS. The Windows host successfully started a RealSense pipeline and received synchronized depth/color frames at `640x480`.

## Notes

- This does not invalidate the prior Mac smoke result. The Mac blocker remains scoped to macOS Tahoe + Homebrew librealsense streaming behavior.
- The camera is still D435, not D435i: `product_id=0B07`, no IMU dependency should be assumed.
- Firmware observed on Windows is `5.17.0.10`, newer than the earlier Mac evidence (`5.15.1.55`).
- Windows can be used as a quick RGB-D bench test host. URHYNIX robot integration should still target Pi4/ROS2 for the live robot flow.

## Cleanup

The temporary local venv and pip cache used for the smoke test were removed after the test. `git status --short` was clean before documentation edits.
