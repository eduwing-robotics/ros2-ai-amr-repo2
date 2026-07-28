# Unity 관제 — 로봇 위치 지정 · 표시

## 한 줄 요약

RViz에서 **2D Pose Estimate**로 찍던 일은 Unity에서도 같고,
Unity → ROS **`/initialpose`**, 화면 표시는 ROS **`/amcl_pose`** 를 읽으면 된다.

---

## 1. 초기 위치 (사람이 한 번 맞춤)

실제 로봇을 맵 위 어디에 둘지 **사람이 지정**해야 AMCL이 맞다.

| 도구 | 동작 |
|------|------|
| RViz | 2D Pose Estimate 클릭 |
| Unity | 맵에서 위치·방향 지정 후 `/initialpose` publish |

메시지: `geometry_msgs/PoseWithCovarianceStamped`
- `header.frame_id = "map"`
- `pose.pose`: x, y, quaternion(z,w) from yaw

이후 AMCL이 `/amcl_pose`와 TF `map`→`base_footprint`를 갱신한다.

## 2. 실시간 위치 (Unity가 그리는 로봇)

Unity는 위치를 새로 계산하지 않는다. 구독만 한다.

- 토픽: `/amcl_pose`
- 또는 TF: `map` → `base_footprint`
- Gen.G: `ROS_DOMAIN_ID=1`

맵 이미지는 `maps/museum_map.pgm` + `museum_map.yaml`의 `resolution`, `origin`을 쓴다.
픽셀 Y축은 ROS map Y와 반대인 경우가 많다.

## 3. 주행 명령

| Unity 동작 | ROS |
|------------|-----|
| 목적지 1곳 | `nav2_msgs/action/NavigateToPose` |
| 경유 여러 곳 | `NavigateThroughPoses` / `FollowWaypoints` |
| 정지 | 활성 Action cancel |

모든 pose는 `frame_id=map`, yaw → quaternion.

## 4. 권장 구조

```
Unity UI  ←→  Gateway(ROS2 node)  ←→  Nav2 / AMCL
                 │
                 ├─ publish /initialpose
                 ├─ subscribe /amcl_pose  → Unity로 전달
                 └─ Nav2 actions
```

Unity가 Nav2 Action 클라이언트를 직접 복잡하게 다루기보다 Gateway를 두는 편이 안전하다.
