---
name: robot-ip-detect-fallback
description: mDNS(`urhynix-robot.local`/`rb.local`)가 깨져서 ssh alias도 안 갈 때, ARP 캐시 + 라즈베리 OUI + known_hosts ed25519 키 매칭으로 젠지/티원의 새 IP를 신원 보장으로 찾는 fallback 절차. URHYNIX DHCP drift + Wi-Fi 대역 변동(0.x↔10.x) 환경 표준.
user_invocable: true
tags: [network, dhcp, mdns, ssh, urhynix-fallback]
trigger: "ssh urhynix-robot 또는 ssh t1이 'Could not resolve hostname'으로 실패하고 IP가 어디로 갔는지 모를 때"
version: 1
---

# Robot IP Detect Fallback (mDNS 깨졌을 때 신원 보장 추적)

## 언제 쓰나

- `ssh t1` / `ssh urhynix-robot`이 `Could not resolve hostname`으로 떨어질 때
- `ip-drift-resync`의 `tb3-ip` MAC sweep도 실패할 때
- Wi-Fi 라우터 대역이 바뀐 직후 (`192.168.0.x` ↔ `192.168.10.x` 같은 점프)
- 박물관/사무실 이동 후 첫 ssh 시도

## 추적 3단

### 단계 1 — ARP에서 라즈베리 OUI 후보 추리기

라즈베리 OUI:
- `b8:27:eb` (Pi 3 이전)
- `dc:a6:32` (Pi 3B+, Pi 4)
- `e4:5f:01` (Pi CM4)
- `2c:cf:67` (Pi 5)
- `d8:3a:dd` (Pi 5, CM5, 신형 Pi 4)

```bash
# 현재 Mac이 붙은 서브넷 자동 추출
SUBNET=$(ifconfig en0 | awk '/inet /{split($2,a,"."); print a[1]"."a[2]"."a[3]}')
echo "subnet: $SUBNET"

# 라즈베리 OUI 매칭만 출력
arp -a | grep -E "$SUBNET\." | grep -iE "b8:27:eb|dc:a6:32|e4:5f:01|2c:cf:67|d8:3a:dd"
```

후보 IP 리스트가 나옴 (보통 2~10개).

### 단계 2 — SSH(22) 열림 + 우분투 배너 확인

```bash
for ip in <후보 IP 들>; do
  banner=$(echo "" | nc -w 1 $ip 22 2>&1 | head -1)
  echo "  $ip → $banner"
done
```

기대 배너: `SSH-2.0-OpenSSH_9.6p1 Ubuntu-3ubuntu13.16` (Ubuntu 24.04 jazzy 라인).

### 단계 3 — known_hosts ed25519 키 매칭 (신원 보장)

가장 강력한 단서. **MAC이 바뀌어도 ed25519 호스트키는 동일**.

```bash
# 옛 알려진 IP의 키 추출
OLD_KEY=$(ssh-keygen -F 192.168.0.250 2>/dev/null | grep "ssh-ed25519" | awk '{print $3}')
echo "옛 .0.250 키 fingerprint head: ${OLD_KEY:0:30}..."

# 후보 IP 각각의 ed25519 키 받아서 비교
for ip in <후보 IP 들>; do
  NEW_KEY=$(ssh-keyscan -t ed25519 -T 2 $ip 2>/dev/null | awk '/ssh-ed25519/{print $3}')
  if [ "$NEW_KEY" = "$OLD_KEY" ]; then
    echo "✅ $ip = 옛 .0.250과 동일 머신 (T1)"
  fi
done
```

키가 일치하면 **MAC/IP가 바뀌어도 같은 라즈베리** 확정.

## 실제 사례 (2026-06-10)

| 항목 | 옛 (~06-04) | 새 (06-10) |
|------|------------|-----------|
| T1 IP | `192.168.0.250` | **`192.168.10.250`** |
| T1 SSH key | `ed25519 AAAAC3...8jan` | 동일 ✅ |
| Wi-Fi 대역 | `192.168.0.x` | `192.168.10.x` |
| mDNS `rb.local` | OK였음 | 실패 |
| 발견 경로 | mDNS | OUI `d8:3a:dd` + ed25519 매칭 |

`ssh t1@<새IP>`로 즉시 들어가짐 (ed25519 키 이미 신뢰 등록).

## ip-drift-resync와의 관계

- `ip-drift-resync` = Unity Scene + Script + known_hosts 일괄 patch (목적지 IP가 결정된 후)
- 이 스킬 = "목적지 IP가 뭔지 모를 때" 신원 보장으로 결정 (이 스킬 → ip-drift-resync 순)

## 한 줄 요약

mDNS가 죽었어도 ARP OUI + ed25519 host key는 안 죽는다. 두 개로 협공하면 라즈베리 신원은 거의 항상 잡힌다.
