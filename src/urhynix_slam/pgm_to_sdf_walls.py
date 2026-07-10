#!/usr/bin/env python3
# pgm_to_sdf_walls.py — ROS occupancy grid(.pgm/.yaml)의 벽 픽셀을 그리디 최대사각형 커버링으로 분해해
# Map25DView(SdfWallSpawner)가 읽는 Gazebo SDF 벽 박스(<link name="wall_N">)로 변환.
# 사용: python3 scripts/pgm_to_sdf_walls.py <src.pgm> <src.yaml> <out.sdf> [wallHeight=0.3] [world_name]
import sys, re


def load_pgm(path):
    with open(path, 'rb') as f:
        assert f.readline().strip() == b'P5', "P5(binary) PGM만 지원"
        line = f.readline()
        while line.startswith(b'#'):
            line = f.readline()
        w, h = map(int, line.split())
        f.readline()  # maxval
        return w, h, f.read(w * h)


def occ_mask(w, h, data, thresh=50):
    return [[1 if data[y * w + x] < thresh else 0 for x in range(w)] for y in range(h)]


# 이진 격자에서 넓이가 가장 큰 축정렬 사각형 1개 찾기(히스토그램 방식). 반환: (top,left,bottom,right) 픽셀 경계(포함) 또는 None.
def largest_rectangle(mask, h, w):
    best_area, best_rect = 0, None
    heights = [0] * w
    for y in range(h):
        for x in range(w):
            heights[x] = heights[x] + 1 if mask[y][x] else 0
        stack = []
        for x in range(w + 1):
            cur = heights[x] if x < w else 0
            while stack and heights[stack[-1]] >= cur:
                top_i = stack.pop()
                height = heights[top_i]
                left = stack[-1] + 1 if stack else 0
                right = x - 1
                area = height * (right - left + 1)
                if area > best_area:
                    best_area, best_rect = area, (y - height + 1, left, y, right)
            stack.append(x)
    return best_rect


def extract_rects(mask, h, w, min_area_px=2, max_walls=80):
    rects = []
    for _ in range(max_walls):
        r = largest_rectangle(mask, h, w)
        if r is None:
            break
        top, left, bottom, right = r
        area = (bottom - top + 1) * (right - left + 1)
        if area < min_area_px:
            break
        rects.append(r)
        for y in range(top, bottom + 1):
            for x in range(left, right + 1):
                mask[y][x] = 0
    return rects


def main():
    if len(sys.argv) < 4:
        print("사용: pgm_to_sdf_walls.py <src.pgm> <src.yaml> <out.sdf> [wallHeight=0.3] [world_name]")
        sys.exit(1)
    pgm, yaml_path, out_sdf = sys.argv[1], sys.argv[2], sys.argv[3]
    wall_h = float(sys.argv[4]) if len(sys.argv) > 4 else 0.3
    world_name = sys.argv[5] if len(sys.argv) > 5 else "walls"

    txt = open(yaml_path).read()
    res = float(re.search(r"resolution:\s*([\d.]+)", txt).group(1))
    o = re.search(r"origin:\s*\[([-\d.]+),\s*([-\d.]+)", txt)
    ox, oy = float(o.group(1)), float(o.group(2))

    w, h, data = load_pgm(pgm)
    mask = occ_mask(w, h, data)
    rects = extract_rects(mask, h, w)

    # ROS map_server 관례: pgm row0=이미지 상단=world y 최대, col0=이미지 좌측=world x 최소(=ox).
    def px_to_world(px, py):
        return ox + px * res, oy + (h - 1 - py) * res

    links = []
    for i, (top, left, bottom, right) in enumerate(rects):
        x0, y0 = px_to_world(left, bottom)   # 하단 행 → world y 작은 쪽
        x1, y1 = px_to_world(right, top)      # 상단 행 → world y 큰 쪽
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        size_x, size_y = abs(x1 - x0) + res, abs(y1 - y0) + res
        links.append((i, cx, cy, wall_h / 2.0, size_x, size_y, wall_h))

    with open(out_sdf, 'w') as f:
        f.write(f'<?xml version="1.0" ?>\n<sdf version="1.9">\n  <world name="{world_name}">\n')
        f.write('    <physics name="1ms" type="ignored"><max_step_size>0.001</max_step_size>'
                '<real_time_factor>1.0</real_time_factor></physics>\n')
        f.write('    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>\n')
        f.write('    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>\n')
        f.write('    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>\n')
        f.write('    <light name="sun" type="directional"><pose>0 0 10 0 0 0</pose>'
                 '<diffuse>1 1 1 1</diffuse><specular>0.2 0.2 0.2 1</specular>'
                 '<direction>-0.5 0.5 -1</direction></light>\n')
        f.write('    <model name="walls">\n      <static>true</static>\n')
        for i, cx, cy, cz, sx, sy, sz in links:
            f.write(f'      <link name="wall_{i}">\n')
            f.write(f'        <pose>{cx:.4f} {cy:.4f} {cz:.4f} 0 0 0</pose>\n')
            f.write(f'        <collision name="collision"><geometry><box><size>{sx:.4f} {sy:.4f} {sz:.4f}</size>'
                     f'</box></geometry></collision>\n')
            f.write(f'        <visual name="visual"><geometry><box><size>{sx:.4f} {sy:.4f} {sz:.4f}</size>'
                     f'</box></geometry><material><ambient>0.02 0.02 0.02 1</ambient>'
                     f'<diffuse>0.02 0.02 0.02 1</diffuse></material></visual>\n')
            f.write('      </link>\n')
        f.write('    </model>\n  </world>\n</sdf>\n')

    print(f"{out_sdf}: 벽 {len(links)}개 생성")


if __name__ == '__main__':
    main()
