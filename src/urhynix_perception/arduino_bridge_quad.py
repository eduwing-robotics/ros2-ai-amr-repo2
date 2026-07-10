#!/usr/bin/env python3
"""
URHYNIX Arduino(quad_security.ino) → ROS2 + Supabase bridge — 4센서 버전.
구버전 arduino_bridge.py(LDR/PIR)를 대체한다. LDR 회로 제거 → /sensors/ldr 폐기.
시리얼(/dev/tb3_arduino @9600)에서 [MOTION]/[CLEAR]/[SOUND]/[TEMP] 라인을 파싱해
/sensors/pir(Bool)·/sensors/sound(Int32 swing)·/sensors/temp(Int32 raw)·
/sensors/laser(Bool, PIR 종속 송신부) 4토픽 발행 + PIR/소음 시 Supabase events insert.
레이저 수신부는 납땜문제로 미결선 → laser는 송신 actuator 상태(=PIR)만 반영(Unity는 비활성 표시).
"""
import json
import math
import os
import re
import sys
import threading
import time
import urllib.request
import urllib.error

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Int32
from nav_msgs.msg import Odometry

import serial


SERIAL_DEVICE = "/dev/tb3_arduino"
SERIAL_BAUD = 9600

RE_MOTION = re.compile(r"^\[MOTION\]")
RE_CLEAR = re.compile(r"^\[CLEAR")
RE_SOUND = re.compile(r"^\[SOUND\]\s+(DETECTED|quiet)\s+\(swing=(\d+)\)")
RE_TEMP = re.compile(r"^\[TEMP\]\s+A0\s+raw=(\d+)")


def _load_env_file(path="/etc/urhynix.env"):
    """dotenv-style loader. Lines: KEY=value. Comments with #. Quotes stripped."""
    if not os.path.exists(path):
        return
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                v = v.strip().strip("'").strip('"')
                os.environ.setdefault(k.strip(), v)
    except OSError:
        pass


_load_env_file()

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://ueupkrxwybuuqxflstvg.supabase.co"
).rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SESSION_ID = os.environ.get(
    "URHYNIX_SESSION_ID", "00000000-0000-0000-0000-000000000001"
)
ROBOT_ID = os.environ.get("URHYNIX_ROBOT_ID", "tb3_2")


def quaternion_to_yaw(q) -> float:
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class ArduinoBridge(Node):
    def __init__(self):
        super().__init__("arduino_bridge")

        # publishers — 4센서 계약
        self.pub_pir = self.create_publisher(Bool, "/sensors/pir", 10)
        self.pub_sound = self.create_publisher(Int32, "/sensors/sound", 10)
        self.pub_temp = self.create_publisher(Int32, "/sensors/temp", 10)
        self.pub_laser = self.create_publisher(Bool, "/sensors/laser", 10)

        # cached pose from /odom
        self._last_x = 0.0
        self._last_y = 0.0
        self._last_yaw = 0.0
        self._have_odom = False
        self.create_subscription(Odometry, "/odom", self._on_odom, 10)

        # serial
        try:
            self.ser = serial.Serial(SERIAL_DEVICE, SERIAL_BAUD, timeout=1)
        except serial.SerialException as e:
            self.get_logger().error(f"open serial failed: {e}")
            raise
        time.sleep(2.0)  # Arduino DTR reset

        self.get_logger().info(
            f"bridging {SERIAL_DEVICE} @ {SERIAL_BAUD} → "
            f"/sensors/pir, /sensors/sound, /sensors/temp, /sensors/laser"
        )
        if SUPABASE_KEY:
            self.get_logger().info(
                f"Supabase insert ENABLED → {SUPABASE_URL}/rest/v1/events  "
                f"(session_id={SESSION_ID}, robot_id={ROBOT_ID})"
            )
        else:
            self.get_logger().warn(
                "SUPABASE_KEY not set — DB insert DISABLED "
                "(set /etc/urhynix.env or env var to enable)"
            )

        self._stop = threading.Event()
        self._t = threading.Thread(target=self._read_loop, daemon=True)
        self._t.start()

    # -------- /odom --------
    def _on_odom(self, msg: Odometry):
        self._have_odom = True
        self._last_x = msg.pose.pose.position.x
        self._last_y = msg.pose.pose.position.y
        self._last_yaw = quaternion_to_yaw(msg.pose.pose.orientation)

    # -------- Supabase events insert --------
    def _insert_event(self, event_type: str, severity: int, raw: dict) -> tuple[bool, str]:
        if not SUPABASE_KEY:
            return False, "SUPABASE_KEY-not-set"
        url = f"{SUPABASE_URL}/rest/v1/events"
        body = {
            "session_id": SESSION_ID,
            "robot_id": ROBOT_ID,
            "event_type": event_type,
            "severity": severity,
            "x": float(self._last_x),
            "y": float(self._last_y),
            "theta": float(self._last_yaw),
            "raw_payload": raw,
        }
        req = urllib.request.Request(
            url,
            method="POST",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=4) as resp:
                return resp.status in (200, 201, 204), f"http {resp.status}"
        except urllib.error.HTTPError as e:
            return False, f"http {e.code}: {e.read().decode('utf-8', errors='replace')[:160]}"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    # -------- serial → ROS2 + DB --------
    def _read_loop(self):
        while not self._stop.is_set():
            try:
                raw = self.ser.readline()
            except Exception as e:
                self.get_logger().warn(f"serial read error: {e}")
                time.sleep(0.5)
                continue
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            # --- PIR (+ 레이저 송신부 종속) ---
            if RE_MOTION.match(line):
                self.pub_pir.publish(Bool(data=True))
                self.pub_laser.publish(Bool(data=True))  # 송신 actuator ON
                ok, info = self._insert_event(
                    "pir",
                    3,
                    {
                        "source": "arduino_bridge_quad",
                        "label": "MOTION",
                        "ts_unix": int(time.time()),
                        "have_odom": self._have_odom,
                    },
                )
                self.get_logger().info(f"PIR motion · DB insert: {info}")
                continue
            if RE_CLEAR.match(line):
                self.pub_pir.publish(Bool(data=False))
                self.pub_laser.publish(Bool(data=False))
                continue

            # --- SOUND (swing 값, 펌웨어가 상태 변화 시에만 발신) ---
            m = RE_SOUND.match(line)
            if m:
                detected = m.group(1) == "DETECTED"
                try:
                    swing = int(m.group(2))
                except ValueError:
                    swing = 0
                self.pub_sound.publish(Int32(data=swing))
                if detected:
                    ok, info = self._insert_event(
                        "sound",
                        2,
                        {
                            "source": "arduino_bridge_quad",
                            "label": "SOUND",
                            "swing": swing,
                            "ts_unix": int(time.time()),
                            "have_odom": self._have_odom,
                        },
                    )
                    self.get_logger().info(f"SOUND detected (swing={swing}) · DB insert: {info}")
                continue

            # --- TEMP (raw A0, 1초 주기) ---
            m = RE_TEMP.match(line)
            if m:
                try:
                    self.pub_temp.publish(Int32(data=int(m.group(1))))
                except ValueError:
                    pass
                continue

    def destroy_node(self):
        self._stop.set()
        try:
            self.ser.close()
        except Exception:
            pass
        return super().destroy_node()


def main():
    rclpy.init()
    node = ArduinoBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    sys.exit(main() or 0)
