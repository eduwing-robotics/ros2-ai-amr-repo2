# Robot2 RealSense D435 ROS2 smoke (2026-06-01)

> Robot2 at `t1@192.168.0.250` was validated with Intel RealSense D435 on Ubuntu 24.04.4 + ROS 2 Jazzy. This confirms the D435 is usable on the live robot path, not only on the Windows bench host.

## Environment

| Item | Value |
|---|---|
| Robot | Robot2 |
| SSH | `t1@192.168.0.250` |
| Hostname | `rb` |
| OS | Ubuntu 24.04.4 LTS |
| Kernel | `6.8.0-1057-raspi` |
| Architecture | `arm64` |
| ROS distro | Jazzy |
| Camera | Intel RealSense D435 |

## Packages installed

```bash
sudo apt install -y \
  v4l-utils \
  ros-jazzy-realsense2-camera \
  ros-jazzy-realsense2-description \
  ros-jazzy-librealsense2
```

Installed versions observed during launch:

| Package/runtime | Version |
|---|---|
| RealSense ROS | `4.57.7` |
| LibRealSense | `2.57.7` |

## USB and device detection

`lsusb` showed the camera on the USB 3 root hub:

```text
Bus 002 Device 002: ID 8086:0b07 Intel Corp. RealSense D435
```

Initial non-root `rs-enumerate-devices -s` failed with `/dev/video* Permission denied`. Fix applied:

```bash
sudo usermod -aG video,plugdev t1
```

After re-login, normal user enumeration passed:

```text
Device Name                   Serial Number       Firmware Version
Intel RealSense D435          254522075185        5.17.0.10
```

`v4l2-ctl --list-devices` showed the D435 as:

```text
Intel(R) RealSense(TM) Depth Ca (usb-0000:01:00.0-2):
        /dev/video0
        /dev/video1
        /dev/video2
        /dev/video3
        /dev/video4
        /dev/video5
        /dev/media4
        /dev/media5
```

## ROS launch

Command:

```bash
ros2 launch realsense2_camera rs_launch.py \
  align_depth.enable:=true \
  pointcloud.enable:=true
```

Key launch output:

```text
Device with serial number 254522075185 was found.
Device with name Intel RealSense D435 was found.
Device USB type: 3.2
Device FW version: 5.17.0.10
Device Product ID: 0x0B07
Open profile: Depth Z16 848x480x30
Open profile: Color RGB8 640x480x30
RealSense Node Is Up!
```

## ROS topics

Topics observed:

```text
/camera/camera/aligned_depth_to_color/camera_info
/camera/camera/aligned_depth_to_color/image_raw
/camera/camera/color/camera_info
/camera/camera/color/image_raw
/camera/camera/color/metadata
/camera/camera/depth/camera_info
/camera/camera/depth/image_rect_raw
/camera/camera/depth/metadata
/camera/camera/extrinsics/depth_to_color
```

Topic rate checks:

| Topic | Result |
|---|---|
| `/camera/camera/color/image_raw` | ~`30.03 Hz` |
| `/camera/camera/depth/image_rect_raw` | ~`30.01 Hz` |
| `/camera/camera/aligned_depth_to_color/image_raw` | ~`29.99 Hz` |

The `timeout` wrapper produced `rcl_shutdown already called` on two `ros2 topic hz` exits. The stream rates were already measured successfully; this is a shutdown warning, not a camera failure.

## Verdict

PASS. Robot2 can run the RealSense D435 through ROS 2 Jazzy at 30Hz for color, depth, and aligned depth. Next useful tests are obstacle/low-wall depth visibility, RGB framing for protected assets, and synchronized recording with odom/pose data.
