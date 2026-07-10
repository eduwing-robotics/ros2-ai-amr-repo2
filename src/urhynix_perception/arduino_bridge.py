#!/usr/bin/env python3
"""
URHYNIX Arduino → ROS2 + Supabase bridge

Subscribes to nothing on Arduino, reads raw serial lines from /dev/tb3_arduino
(Arduino UNO PIR + LDR sketch) and:

  ROS2 publish:
    - /sensors/pir   std_msgs/Bool   (true on [MOTION], false on [CLEAR])
    - /sensors/ldr   std_msgs/Int32  (raw A0 value 0..1023)

  ROS2 subscribe:
    - /odom          nav_msgs/Odometry (caches last x, y, yaw for DB events)

  Supabase insert (PIR 감지 시 events 한 줄):
    POST {SUPABASE_URL}/rest/v1/events
    body: { session_id, robot_id, event_type='pir', severity=3, x, y, theta, raw_payload }

ENV (RPi side; loaded from /etc/urhynix.env if present, else os.environ):
  SUPABASE_URL          (default: https://oucgzkbqrzbwxxffmmqt.supabase.co)
  SUPABASE_KEY          (required; publishable or service_role)
  URHYNIX_SESSION_ID    (default: seed session 00000000-...-0001)
  URHYNIX_ROBOT_ID      (default: tb3_1)

Run on the robot:
  source /opt/ros/jazzy/setup.bash
  source ~/turtlebot3_ws/install/setup.bash
  python3 arduino_bridge.py

Or via helper from Mac/Linux:
  tb3-bridge
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
RE_LDR = re.compile(r"^\[LDR\]\s+A0=(\d+)")

# LDR edge-trigger thresholds (hysteresis to avoid chatter)
LDR_DARK_ENTER = 200   # A0 < 200  → "어두움 진입" → events insert (event_type='dark')
LDR_DARK_EXIT = 250    # A0 >= 250 → state reset (insert 없음, 다음 진입 대비)


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
ROBOT_ID = os.environ.get("URHYNIX_ROBOT_ID", "tb3_1")


def quaternion_to_yaw(q) -> float:
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class ArduinoBridge(Node):
    def __init__(self):
        super().__init__("arduino_bridge")

        # publishers
        self.pub_pir = self.create_publisher(Bool, "/sensors/pir", 10)
        self.pub_ldr = self.create_publisher(Int32, "/sensors/ldr", 10)

        # cached pose from /odom
        self._last_x = 0.0
        self._last_y = 0.0
        self._last_yaw = 0.0
        self._have_odom = False
        self.create_subscription(Odometry, "/odom", self._on_odom, 10)

        # LDR edge-trigger state
        self._dark_state = False

        # serial
        try:
            self.ser = serial.Serial(SERIAL_DEVICE, SERIAL_BAUD, timeout=1)
        except serial.SerialException as e:
            self.get_logger().error(f"open serial failed: {e}")
            raise
        time.sleep(2.0)  # Arduino DTR reset

        self.get_logger().info(
            f"bridging {SERIAL_DEVICE} @ {SERIAL_BAUD} → /sensors/pir, /sensors/ldr"
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

            if RE_MOTION.match(line):
                self.pub_pir.publish(Bool(data=True))
                ok, info = self._insert_event(
                    "pir",
                    3,
                    {
                        "source": "arduino_bridge",
                        "label": "MOTION",
                        "ldr_hint": None,
                        "ts_unix": int(time.time()),
                        "have_odom": self._have_odom,
                    },
                )
                self.get_logger().info(f"PIR motion · DB insert: {info}")
            elif RE_CLEAR.match(line):
                self.pub_pir.publish(Bool(data=False))
            else:
                m = RE_LDR.match(line)
                if m:
                    try:
                        v = int(m.group(1))
                        self.pub_ldr.publish(Int32(data=v))
                        # edge-trigger 'dark' event (hysteresis)
                        if not self._dark_state and v < LDR_DARK_ENTER:
                            self._dark_state = True
                            ok, info = self._insert_event(
                                "dark",
                                1,
                                {
                                    "source": "arduino_bridge",
                                    "label": "dark",
                                    "ldr": v,
                                    "ts_unix": int(time.time()),
                                    "have_odom": self._have_odom,
                                },
                            )
                            self.get_logger().info(
                                f"LDR dark enter (A0={v}) · DB insert: {info}"
                            )
                        elif self._dark_state and v >= LDR_DARK_EXIT:
                            self._dark_state = False
                            self.get_logger().info(
                                f"LDR dark exit (A0={v}) — state reset"
                            )
                    except ValueError:
                        pass

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
