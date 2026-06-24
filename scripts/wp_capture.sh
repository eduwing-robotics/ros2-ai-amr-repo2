#!/usr/bin/env bash
# wp_capture.sh — 티원(tb3_1) 현재 pose를 도메인 210에서 읽기전용으로 캡처해 웨이포인트 파일에 1행 추가.
# 사용: bash scripts/wp_capture.sh <label>   (예: WP1 / WP1_head / START)
# 비침습: tf2_echo는 순수 listener라 텔레옵/라이다/Nav2에 영향 없음.
# 출력: /Users/family/Downloads/wp_captures.yaml (append) + 화면에 캡처값.
set -euo pipefail

LABEL="${1:?label 필요 (예: WP1)}"
T1="${T1_HOST:-t1@192.168.10.250}"
OUT="${WP_OUT:-/Users/family/Downloads/wp_captures.yaml}"

RAW=$(ssh -o ConnectTimeout=8 -o BatchMode=yes -o ControlMaster=no "$T1" \
  'source /opt/ros/jazzy/setup.bash 2>/dev/null; export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET; timeout 6 ros2 run tf2_ros tf2_echo map base_footprint 2>/dev/null | head -7' 2>/dev/null)

python3 - "$LABEL" "$OUT" <<PY
import sys,re,math,os
label,out=sys.argv[1],sys.argv[2]
raw="""$RAW"""
mt=re.search(r"Translation:\s*\[([-\d.]+),\s*([-\d.]+)",raw)
mr=re.search(r"RPY \(radian\)\s*\[[-\d.]+,\s*[-\d.eE]+,\s*([-\d.]+)",raw)
if not (mt and mr):
    print("FAIL: pose 못 읽음 (로봇/도메인 확인). raw=\n"+raw); sys.exit(1)
x,y=float(mt.group(1)),float(mt.group(2)); yaw=float(mr.group(1))
qz,qw=math.sin(yaw/2),math.cos(yaw/2)
new=not os.path.exists(out)
with open(out,"a") as f:
    if new:
        f.write("# 티원 텔레옵 캡처 웨이포인트 (frame_id: map)\n")
        f.write("# 라벨/순서대로 캡처. position=정지지점, orientation=캡처순간 방향.\nposes:\n")
    f.write(f"  - name: {label}\n")
    f.write(f"    header: {{frame_id: map}}\n")
    f.write(f"    pose:\n")
    f.write(f"      position: {{x: {x:.3f}, y: {y:.3f}, z: 0.0}}\n")
    f.write(f"      orientation: {{x: 0.0, y: 0.0, z: {qz:.4f}, w: {qw:.4f}}}\n")
print(f"✅ [{label}] x={x:.3f} y={y:.3f} yaw={math.degrees(yaw):.1f}°  (qz={qz:.4f} qw={qw:.4f}) → {out}")
PY
