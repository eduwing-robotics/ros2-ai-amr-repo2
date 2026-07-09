# 젠지(tb3_2) 핸드오프 패키지 — 동료용

> 동료가 **젠지 접속방법 + 관련 스킬**을 알고 싶다고 해서 추린 자료 묶음이다.
> URHYNIX 리포 없이 이 폴더만 봐도 젠지에 붙어 주행까지 갈 수 있게 구성.
> 생성: 2026-07-09.

## 읽는 순서

### 0. 먼저 — 접속
| 파일 | 용도 |
|------|------|
| **`GENJI-CONNECT.md`** | ★여기부터. SSH 주소·계정(`kim`)·ROS_DOMAIN_ID(=1)·네트워크 함정·IP 드리프트 대응 |
| `skill-robot-ip-detect-fallback.md` | ssh alias가 안 갈 때 mDNS/ARP/OUI로 실제 IP 찾기 |
| `skill-ip-drift-resync.md` | 찾은 IP로 SSOT(`default_robots.json`)+known_hosts 동기화 |
| `skill-urhynix-ros-domain-diagnose.md` | 노드 중복·`/map`/`/tf` 엉킴·"라이다 안 켜짐" 도메인 진단 |

### 1. 젠지 주행/기동 (본론)
| 파일 | 용도 |
|------|------|
| **`skill-urhynix-genji-nav2-drive.md`** | ★젠지 주행 정본. 비-ns AMCL+Nav2 한방기동(nav_up.sh)→Unity 좌표주행 |
| `skill-urhynix-nav2-waypoint-patrol.md` | 저장 웨이포인트 경로 실주행 표준(localize-before-costmap) |
| `skill-urhynix-fullstack-bringup.md` | 5트랙(배터리·파이카메라·라이다맵·LDR·PIR) 동시 기동 + Unity 검증 |
| `skill-urhynix-odom-marker-quickstart.md` | AMCL 없이 odom-only로 Unity 맵에 위치 마커만 빠르게 |

### 2. 지원
| 파일 | 용도 |
|------|------|
| `skill-robot-camera-bringup.md` | 젠지 Pi Camera v2 노드 + ros_tcp_endpoint 백그라운드 launch |
| `skill-urhynix-robot-shutdown.md` | 젠지·티원 안전 종료(sudo 비번 주입 + ping 검증) |

## 참고

- 이 파일들은 URHYNIX 리포 `.claude/skills/<name>/SKILL.md`의 사본이다(2026-07-09 시점). 스킬이 참조하는 **실행 스크립트**(`nav_up.sh`, `_robot_nav_up.sh` 등)는 리포 `scripts/`에 있음 — 필요하면 요청.
- 젠지 vs 티원: **도메인 다름**(젠지 1 / 티원 2), 스택 다름(젠지 비-ns 단일 / 티원 tb3_1 네임스페이스). 이 패키지는 **젠지** 기준.
- sudo 비번은 git 미포함 — 팀 채널 별도공유.

---
**한줄정리**: `GENJI-CONNECT.md`(접속)부터 → `skill-urhynix-genji-nav2-drive.md`(주행 정본) 순. 안 붙으면 ip-detect-fallback→ip-drift-resync. 젠지=도메인 1, 계정 kim.
