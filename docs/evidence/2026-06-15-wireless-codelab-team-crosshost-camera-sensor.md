<!-- 
URHYNIX 2026-06-15 후반 작업 결과
주제: 무선 네트워크 통일(codelab_robot_team_2_5G) + 양 로봇 카메라/센서 cross-host multicast 검증 + 망 안정성 경고
기록자: 주인님 검증사항 정리
-->

# 2026-06-15 (후반) — codelab_robot_team_2_5G 무선 통일 + 양 로봇 카메라/센서 cross-host PASS + 망 불안정 경고

## 무선 네트워크 변천 및 최종 상태

### 시도 경로
1. **팀 전용 와이파이(이전 세션)** — AP isolation 아님. 다만 DDS multicast 차단으로 cross-host discovery 불가.
2. **`codelab_5G` 전환 시도** — 5GHz, 공유기가 로봇 범위 밖. 젠지 스캔: "No network found" (신호 0).
3. **최종 선택: `codelab_robot_team_2_5G`** — 로봇이 기존에 연결된 SSID(5200MHz), Mac도 이 SSID로 통일.

### 최종 네트워크 구성
```
SSID: codelab_robot_team_2_5G (5200MHz)
Mac:        192.168.10.101 (en0 무선)
티원(tb3_1): 192.168.10.250 (wlan0)
젠지(tb3_2): 192.168.10.87  (wlan0)
ROS_DOMAIN_ID: 210 (이전 세션 완료)
```

**주의**: 모든 IP는 DHCP drift. 다음 세션 진입 시 `arp-scan` 또는 `mDNS hostname` 재확인.

---

## cross-host DDS multicast 검증 PASS

### 실험: talker/listener 양방향 수신
```bash
# 젠지 talker (listener 없음)
$ ros2 run demo_nodes_cpp talker

# 티원 listener (subscriber)
$ ros2 run demo_nodes_cpp listener
[INFO] I heard: [Hello World: X]  ← 수신 PASS
```

**결론**: `codelab_robot_team_2_5G`는 **multicast 정상 작동**.  
이전 팀 와이파이(AP isolation이라 생각했지만 실제는 multicast 차단)과 달라, STATIC_PEERS 우회법 불필요.  
(robot-camera-bringup §F에 우회법은 이미 기록 — multicast 차단 망 대비용으로 보존)

---

## 양 로봇 카메라 + 젠지 센서 전부 cross-host 결선 PASS

### 데이터 흐름 최종 검증
```
[티원 RealSense D435]
  └─ /tb3_1/camera/color/image_raw/compressed (30Hz, 로컬)
      └─ ros_tcp_endpoint (유일한 endpoint)
          └─ TCP port 10000 → Unity

[젠지 Pi Camera v2]
  └─ /tb3_2/camera/image_raw/compressed (30Hz, cross-host multicast)
      └─ 동일 endpoint (port 10000)
          └─ Unity

[젠지 Arduino LDR/PIR]
  ├─ /sensors/ldr (Int32, 조도)
  └─ /sensors/pir (Bool, 인체감지)
      └─ arduino_bridge.py (cross-host 수신 확인)
          └─ 동일 endpoint (port 10000)
              └─ Unity
```

### 검증 항목
- ✅ **카메라 2개** — Ti원 RealSense D435 + 젠지 Pi Camera v2 동시 발행 (각 30Hz)
- ✅ **카메라 압축** — 모두 `compressed` 토픽 (네트워크 효율)
- ✅ **센서 수신** — `/sensors/ldr`, `/sensors/pir` cross-host multicast 수신 확인 (arduino_bridge.py 로그)
- ✅ **Unity RegisterSubscriber** — 전부 OK, 구독 시작. Unity Play 중.
- ✅ **단일 endpoint** — 티원 ros_tcp_endpoint(port 10000)이 양 로봇 토픽 수집 완료

---

## 이번 세션 신규 함정 5건

### (a) 젠지 `~/.bashrc` ROS_STATIC_PEERS 잔재
**증상**: cross-host 통신 불안정, 특정 토픽만 오다 안 오다 반복.  
**원인**: 젠지 `~/.bashrc`에 `export ROS_STATIC_PEERS=192.168.10.70` 잔재 (이전 세션 팀 와이파이 대비).  
**해결**: `sed -i '/ROS_STATIC_PEERS/d' ~/.bashrc` → bashrc reload.

### (b) `/dev/tb3_arduino` 심링크 stale
**증상**: arduino_bridge.py 시작 → `[ERROR] Failed to open port: No such file`.  
**원인**: Arduino(USB idVendor 2341, idProduct 0043) → `/dev/ttyACM0`로 재할당됐으나 symlink 여전히 `/dev/tb3_arduino` → old `/dev/ttyACM1`.  
**해결**: `ls -l /dev/ttyACM*` 확인 후 udev rule 재링크 또는 `ln -sf /dev/ttyACM0 /dev/tb3_arduino`.

### (c) RealSense compressed = lazy republish
**증상**: Unity ROS-TCP-Connector 구독 후에도 `/tb3_1/camera/color/image_raw/compressed`가 안 옴.  
**원인**: realsense2_camera는 **구독자 있을 때만 compressed 발행**. 다른 노드가 먼저 구독해야 시작.  
**해결**: ros_tcp_endpoint 띄운 후 → Unity 구독 시작 → realsense 재시작.

### (d) 직결(en5) + 무선(en0) 같은 대역 충돌
**증상**: wlan0 192.168.10.87 수신 잘되다 끊김, eth0도 192.168.10.x 대역 보유 → asymmetric routing 재발.  
**원인**: Mac에서 `en5`(eth0 직결) + `en0`(wlan0 무선) 동시 활성 → default route 혼동.  
**해결**: `ifconfig en5 down` (직결 제거), 무선만 활용. IP 단일화.

### (e) Unity 에디터 background throttle
**증상**: `unityctl play` 토글 후 로그 정지, CPU 0%. Editor가 background로 내려감.  
**원인**: macOS 자동 background throttle. Unity 포커스 필요.  
**해결**: 
- "Edit → Preferences → General → Run In Background" 활성화, 또는
- Editor를 항상 포그라운드 유지 + `osascript "System Events" "Unity" set frontmost`

---

## 다음 세션 주의사항 (높음)

### **codelab_robot_team_2_5G 간헐 끊김 심각**
**증상**: 10회 연속 ping 중 2~3회 100% loss, 회복 1초 내, 빈번 반복.  
**영향**: 시연 도중 "잠깐 끊겼다" 시각적 끊김 불가피 → **신뢰성 낮음**.  
**임시 우회**:
- codelab_5G로 공유기 이동 가능한지 확인 (Wi-Fi 안정성 높음, 다만 로봇 범위 확인 필수).
- 또는 **직결(Mac ↔ 젠지 eth0)로 복귀** + 팀원 mDNS 충돌 회피 ([project_robot_ip_dynamic] + robot-ip-detect-fallback SKILL 참조).

### **다음 진입 5단계 체크리스트**
1. 젠지/티원 켜기 → DHCP IP 재확인 (arp-scan 또는 mDNS hostname)
2. USB `/dev/ttyACM*` 번호 재확인 → `/dev/tb3_arduino` symlink 갱신
3. 양 로봇 `.bashrc` ROS_DOMAIN_ID=210 확인 (ROS_STATIC_PEERS 없음)
4. `turtlebot3_bringup robot.launch.py namespace:=tb3_1` + `namespace:=tb3_2` 실행
5. ros_tcp_endpoint + arduino_bridge.py 실행 후 Unity 구독 시작

### **세션 종료 상태**
- ✅ 젠지: 안전 종료(`poweroff`) 완료, ping 100% loss 확인
- ⚠️ 티원: 망 끊김으로 ssh 셧다운 실패 → **물리 전원 OFF 필요**

---

## Timeline

| 시간 | 작업 |
|------|------|
| 14:00 | `codelab_5G` 시도 → 로봇 신호 0, fallback |
| 14:30 | `codelab_robot_team_2_5G`로 통일, Mac 재연결 |
| 14:45 | talker/listener multicast 검증 PASS |
| 15:00 | 젠지 `.bashrc` ROS_STATIC_PEERS 제거 |
| 15:15 | `/dev/tb3_arduino` symlink 재링크 |
| 15:30 | 양 카메라 + 센서 cross-host 통신 검증 PASS |
| 15:45 | 직결(en5) down, 무선 단일화 |
| 16:00 | 망 안정성 경고, 최종 상태 기록 |
| 16:15 | 세션 종료, 안전 shutdown |

---

## 참고: 이전 함정/SKILL 재활용

- **robot-ip-detect-fallback**: mDNS 실패 시 ARP OUI + ed25519 매칭으로 로봇 신원 추적
- **project_robot_ip_dynamic**: DHCP drift 정상화, next session mDNS 재확인 권장
- **urhynix-team-wifi-isolation-direct-link**: 팀 와이파이 multicast 차단 대비 (현재 codelab_robot_team_2_5G는 multicast OK)
