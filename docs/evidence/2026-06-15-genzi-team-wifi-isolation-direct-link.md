<!--
2026-06-15 젠지 재접속 evidence. 팀 전용 ipTIME 와이파이 AP isolation으로 무선 SSH 전면 불가.
Mac↔젠지 USB이더넷 직결 + Mac bootpd DHCP 서버로 우회 접속 성공. 재현 절차 + 진단 결과 보존.
-->
# 2026-06-15 젠지 재접속 — 팀 와이파이 AP isolation 우회 직결

## 한 줄 결과
팀이 새로 설정한 전용 ipTIME 와이파이가 **AP isolation(클라이언트 격리)**라 무선으로 로봇 SSH 전면 불가. **Mac↔젠지 USB이더넷 직결 + Mac을 `bootpd` DHCP 서버로** 띄워 젠지 eth0에 `192.168.10.50` 할당, `ssh kim@192.168.10.50` PASS.

## 진단 — 격리망 판별 (재현)
```bash
# 인터넷 TCP는 되는데 로컬 TCP가 전부 막히면 = AP isolation 확정
nc -z -w3 1.1.1.1 443            # OK (인터넷 됨)
nc -z -w3 192.168.10.1 80        # 막힘 (공유기 관리조차 무선 차단)
# 같은 서브넷 ping sweep → 수십 대 reachable 이지만 SSH(22) 응답 0개
```
- mDNS(`urhynix-robot.local`) resolve 실패, ARP 라즈베리 OUI 매칭 0, known_hosts ed25519 host key 매칭 0 — fallback 전부 무력화.
- 무력화 원인: 젠지 **ssh host key 재생성** `SHA256:5f39JP0jjYn…` → `SHA256:Z4BBz6FU0in6…` (팀원이 OS/설정 손봄).
- ipTIME 비번 `admin`/`08000800` 있어도 무선에선 관리 UI(`10.1`) HTTP 000. 메인 SSID로 갈아타도 다른 격리망(`192.168.0.x`)이라 동일.

## 우회 — Mac↔젠지 직결 + bootpd DHCP (검증됨)
```bash
# 0) USB-C↔이더넷 어댑터(en5=USB 10/100 LAN) ↔ 젠지 이더넷 직결
ifconfig en5 | grep -E "status|inet"     # status: active (100baseTX) = 물리 링크 OK
#    젠지 eth0는 DHCP 클라이언트라 직결만으론 IP 못 받음 (netstat -I en5 의 Ipkts만 증가)

# 1) en5 같은 대역 수동 IP (sudo 비번 = Mac 로그인 비번)
sudo networksetup -setmanual "USB 10/100 LAN" 192.168.10.200 255.255.255.0

# 2) bootpd.plist 작성 (PlistBuddy)
sudo rm -f /etc/bootpd.plist
sudo /usr/libexec/PlistBuddy \
  -c "Add :dhcp_enabled array" -c "Add :dhcp_enabled:0 string en5" \
  -c "Add :bootp_enabled bool false" \
  -c "Add :Subnets array" \
  -c "Add :Subnets:0:name string en5net" \
  -c "Add :Subnets:0:net_address string 192.168.10.0" \
  -c "Add :Subnets:0:net_mask string 255.255.255.0" \
  -c "Add :Subnets:0:interface string en5" \
  -c "Add :Subnets:0:allocate bool true" \
  -c "Add :Subnets:0:net_range array" \
  -c "Add :Subnets:0:net_range:0 string 192.168.10.50" \
  -c "Add :Subnets:0:net_range:1 string 192.168.10.150" \
  /etc/bootpd.plist

# 3) bootpd 기동 (on-demand, 라벨 com.apple.bootpd)
sudo launchctl enable system/com.apple.bootpd
sudo launchctl load -w /System/Library/LaunchDaemons/bootps.plist

# 4) 5초 내 젠지 lease → SSH
sudo cat /var/db/dhcpd_leases
#   name=kim-desktop  ip_address=192.168.10.50  hw_address=1,2c:cf:67:47:38:2
ssh kim@192.168.10.50                # 키 인증, 비번 fallback 1234
```
> 참고: macOS 인터넷공유(`com.apple.NetworkSharing`)는 수동IP en5를 안 잡아 실패했음. **bootpd 직접 기동이 정답.** 직결해도 젠지 인터넷은 wlan0(팀 와이파이) 경유로 유지됨(eth0+wlan0 동시).

## 젠지 현황 (접속 후 점검)
| 항목 | 값 |
|---|---|
| OS / arch | Ubuntu 24.04.4 LTS / aarch64 |
| ROS2 | `/opt/ros/jazzy` ✅ |
| 워크스페이스 | `~/turtlebot3_ws` (build/install/src) ✅ |
| `~/.bashrc` | `ROS_DOMAIN_ID=210` (예전 230), `TURTLEBOT3_MODEL=burger` |
| hostname | **`kim-desktop`** (예전 `urhynix-robot`) |
| 인터페이스 | eth0=`192.168.10.50`(직결), wlan0=`192.168.10.87`(팀 와이파이) |
| 카메라 | `/dev/video0~19` 인식 (rpicam `--list-cameras` 출력은 별도 확인 필요) |
| 인터넷 | OK (wlan0) |
| 디스크 | 117G 중 15G (13%) |

## 잔여 / 다음 세션
- [ ] `ROS_DOMAIN_ID=210`이 티원/Unity와 일치하는지 확인 (예전 SSOT는 230). 불일치 시 통신 안 됨.
- [ ] (선택) 무선 영구화: 젠지 인터넷 살아있으니 `curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up` → 격리·IP drift 무관. 2026-06-15엔 주인님 "여기까지" 선택으로 보류.
- [ ] Pi Camera 실제 캡처(`rpicam-hello`) + ROS2 토픽 발행 검증.
