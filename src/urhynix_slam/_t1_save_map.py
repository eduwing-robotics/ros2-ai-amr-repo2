# _t1_save_map.py — nav2_map_server 없이 /map OccupancyGrid를 pgm+yaml로 저장
# (티원엔 nav2_map_server 미설치 → slam_toolbox save_map(255 실패) 우회)
# 사용: python3 _t1_save_map.py <out_basename>   (예: arena_depth_v1)
import sys, rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy
from nav_msgs.msg import OccupancyGrid

base = sys.argv[1] if len(sys.argv) > 1 else 'map_out'
rclpy.init()
n = Node('map_saver_py')
got = {'m': None}
qos = QoSProfile(depth=1)
qos.durability = QoSDurabilityPolicy.TRANSIENT_LOCAL   # slam_toolbox /map은 latched
qos.reliability = QoSReliabilityPolicy.RELIABLE
n.create_subscription(OccupancyGrid, '/map', lambda m: got.__setitem__('m', m), qos)
# 최신 latched 맵 수신까지 spin
import time
for _ in range(50):
    rclpy.spin_once(n, timeout_sec=0.2)
    if got['m'] is not None:
        break
m = got['m']
if m is None:
    print('NO_MAP_RECEIVED'); sys.exit(1)

w, h = m.info.width, m.info.height
res = m.info.resolution
ox, oy = m.info.origin.position.x, m.info.origin.position.y
data = m.data

# PGM (P5): 이미지 row 0 = 최상단(최대 y). map_server 관례: free=254 occ=0 unknown=205
buf = bytearray(w * h)
for r in range(h):
    y = h - 1 - r
    for c in range(w):
        v = data[y * w + c]
        buf[r * w + c] = 254 if v == 0 else (0 if v >= 65 else 205)

with open(f'{base}.pgm', 'wb') as f:
    f.write(b'P5\n%d %d\n255\n' % (w, h))
    f.write(bytes(buf))

with open(f'{base}.yaml', 'w') as f:
    f.write(f'image: {base}.pgm\nmode: trinary\nresolution: {res:.6f}\n')
    f.write(f'origin: [{ox:.6f}, {oy:.6f}, 0.0]\nnegate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n')

print(f'SAVED {base} {w}x{h} res={res} origin=[{ox:.3f},{oy:.3f}]')
n.destroy_node(); rclpy.shutdown()
