# 젠지(tb3_2) 핸드오프 패키지 — 동료용

> 동료가 **젠지 접속방법 + 관련 스킬**을 알고 싶다고 해서 추린 자료 묶음이다.
> URHYNIX 리포 없이 이 폴더만 봐도 젠지에 붙어 주행까지 갈 수 있게 구성.
> 생성 2026-07-09 · 최신성 감사 2026-07-09(스테일 3종 제거).

## ★ 현재 기준값 (이게 정본 — 옛 문서와 충돌 시 이걸 따를 것)

| 항목 | 젠지(tb3_2) | 티원(tb3_1) |
|---|---|---|
| 계정 | `kim` | `t1` |
| IP (wlan0, **드리프트함**) | 192.168.20.7 | 192.168.20.101 |
| ROS_DOMAIN_ID | **1** | 2 |
| nav2 스택 | 비-ns 단일(nav_up.sh) | tb3_1 네임스페이스 |

> ⚠️ 과거 문서/스크립트에 `192.168.0.x` 서브넷이나 `ROS_DOMAIN_ID=210/230`이 보이면 **전부 옛 체제**다 — 무시하고 위 표를 쓸 것. 접속 세부는 `GENJI-CONNECT.md`.

## 읽는 순서

### 0. 먼저 — 접속
| 파일 | 용도 |
|------|------|
| **`GENJI-CONNECT.md`** | ★여기부터. SSH·계정 kim·도메인1·네트워크 함정·IP 드리프트 대응 |
| `skill-robot-ip-detect-fallback.md` | ssh alias가 안 갈 때 mDNS/ARP/OUI로 실제 IP 찾기 (본문 예시 IP `0.250`은 옛 서브넷 — 방법만 참고) |
| `skill-ip-drift-resync.md` | 찾은 IP로 SSOT(`default_robots.json`)+known_hosts 동기화 |
| `skill-urhynix-ros-domain-diagnose.md` | 노드 중복·`/map`/`/tf` 엉킴·"라이다 안 켜짐" 도메인 진단 |

### 1. 젠지 주행/기동
| 파일 | 용도 |
|------|------|
| **`skill-urhynix-genji-nav2-drive.md`** | ★젠지 주행 정본. 비-ns AMCL+Nav2 한방기동(nav_up.sh)→Unity 좌표주행 (07-08 PASS) |
| `skill-urhynix-fullstack-bringup.md` | 5트랙(배터리·파이카메라·라이다맵·센서) 동시 기동+Unity 검증. 도메인1 유효. ⚠️센서 트랙은 LDR+PIR 2종 시절 기준 — 현재 4-quad(PIR+레이저+사운드+온도)로 진화했으니 센서 부분은 최신 arduino 스킬 별도 확인 |

### 2. 지원
| 파일 | 용도 |
|------|------|
| `skill-urhynix-robot-shutdown.md` | 젠지·티원 안전 종료(sudo 비번 주입 + ping 검증) |

## 제외한 파일 (스테일/중복 — 필요하면 요청)

| 파일 | 제외 이유 |
|------|------|
| `robot-camera-bringup` | 옛 서브넷(`192.168.0.x`) + 옛 도메인(230) — 현재 기준과 정면 충돌. 카메라 launch 방법(libcamera LD_LIBRARY_PATH)만 유효하니 필요 시 최신값으로 갱신해 전달 |
| `nav2-waypoint-patrol` | 도메인210 구세대 + `genji-nav2-drive`가 대체(중복) |
| `odom-marker-quickstart` | 도메인210 스테일, 보조 quickstart |

## 참고

- 이 파일들은 URHYNIX 리포 `.claude/skills/<name>/SKILL.md`의 사본(2026-07-09 시점). 스킬이 참조하는 실행 스크립트(`nav_up.sh` 등)는 리포 `scripts/`에 있음 — 필요하면 요청.
- 젠지 vs 티원: 도메인 다름(젠지 1 / 티원 2), 스택 다름(젠지 비-ns / 티원 tb3_1 ns). 이 패키지는 **젠지** 기준.
- sudo 비번은 git 미포함 — 팀 채널 별도공유.

---
**한줄정리**: `GENJI-CONNECT.md`→`skill-urhynix-genji-nav2-drive.md` 순. 옛 문서의 `192.168.0.x`/도메인`210/230`은 전부 무시(현재: 젠지=도메인1, 192.168.20.7). 스테일 3종은 제거함.
