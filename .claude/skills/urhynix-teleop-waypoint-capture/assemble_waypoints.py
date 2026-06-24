#!/usr/bin/env python3
# assemble_waypoints.py — wp_capture.sh 캡처본을 읽어 위치(WPn)+방향(WPn_head, 없으면 도착 yaw)을 합쳐
# 정렬된 최종 FollowWaypoints YAML로 조립. WP*_head_start가 있으면 그 WP의 복귀 방향으로 우선 사용.
# 사용: python3 assemble_waypoints.py <captures.yaml> <out.yaml> [--robot tb3_1]
import sys, re, math, argparse

def parse(path):
    txt = open(path).read()
    blocks = re.findall(
        r"  - name: (\S+)\n.*?position: \{x: ([-\d.]+), y: ([-\d.]+).*?orientation: \{x: 0.0, y: 0.0, z: ([-\d.]+), w: ([-\d.]+)\}",
        txt, re.S)
    cap = {}
    for name, x, y, qz, qw in blocks:
        yaw = math.degrees(2*math.atan2(float(qz), float(qw)))
        cap[name] = (float(x), float(y), yaw)
    return cap

def q(yaw_deg):
    y = math.radians(yaw_deg)
    return round(math.sin(y/2), 4), round(math.cos(y/2), 4)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('captures'); ap.add_argument('out')
    ap.add_argument('--robot', default='tb3_1')
    a = ap.parse_args()
    cap = parse(a.captures)

    # WPn 라벨 자동 탐색 (WP1, WP2, ...)
    wp_nums = sorted({int(m.group(1)) for k in cap for m in [re.fullmatch(r'WP(\d+)', k)] if m})
    order = ['START'] + [f'WP{n}' for n in wp_nums]

    final = []
    for label in order:
        if label not in cap:
            print(f"⚠️ {label} 위치 캡처 없음 — 건너뜀"); continue
        x, y, arr_yaw = cap[label]
        # 방향 우선순위: <label>_head_start > <label>_head > 도착 yaw
        head = cap.get(f"{label}_head_start") or cap.get(f"{label}_head")
        yaw = head[2] if head else arr_yaw
        qz, qw = q(yaw)
        final.append((label, x, y, yaw, qz, qw))

    with open(a.out, 'w') as f:
        f.write(f"# {a.robot} 텔레옵 실측 순찰 웨이포인트 (조립본)\n")
        f.write("# 위치=정지 실측, 방향=회전 실측(_head/_head_start) 없으면 도착 yaw\n")
        f.write("# frame_id: map — 같은 저장맵+AMCL에서 FollowWaypoints로 구동\n\n")
        f.write("frame_id: map\nposes:\n")
        for label, x, y, yaw, qz, qw in final:
            f.write(f"  - name: {label}\n    header: {{frame_id: map}}\n    pose:\n")
            f.write(f"      position: {{x: {x:.3f}, y: {y:.3f}, z: 0.0}}\n")
            f.write(f"      orientation: {{x: 0.0, y: 0.0, z: {qz}, w: {qw}}}\n")

    print(f"{len(final)}점 조립 → {a.out}")
    for label, x, y, yaw, *_ in final:
        print(f"  {label:6} x={x:7.3f} y={y:7.3f} yaw={yaw:6.1f}°")

if __name__ == '__main__':
    main()
