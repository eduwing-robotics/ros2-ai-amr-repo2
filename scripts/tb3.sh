# URHYNIX TurtleBot3 helpers — single file for macOS + Linux (Ubuntu)
# Source from your shell rc:
#   echo 'source ~/URHYNIX/scripts/tb3.sh' >> ~/.zshrc    # macOS
#   echo 'source ~/URHYNIX/scripts/tb3.sh' >> ~/.bashrc   # Ubuntu
#
# Requires: ssh, nc, ping, expect, ipconfig/ip, arp/ip neigh
# Optional: scp (for tb3-up), xdg-open/open (for tb3-vnc), Unity Hub (for tb3-unity)

# ---- Tunables ----
export TB3_MAC_PATTERN='2c:cf:67:47:38:0?3'   # robot Wi-Fi MAC (leading-zero tolerant)
export TB3_USER='kim'
export TB3_HOSTNAME='urhynix-robot'             # mDNS hostname (avahi publishes <hostname>.local)
export TB3_ROBOT_IP_HINT='192.168.10.87'       # last known (fallback only)
export TB3_LAN_CIDR='192.168.10'                # /24 to sweep (fallback only)

# Passwords live OUTSIDE the repo. Put them in ~/.tb3rc (see scripts/tb3rc.example):
#   export TB3_PASSWORD='your-ssh-password'
#   export TB3_VNC_PASSWORD='your-vnc-password'
[ -f "$HOME/.tb3rc" ] && . "$HOME/.tb3rc"
: "${TB3_PASSWORD:=}"
: "${TB3_VNC_PASSWORD:=}"

# Unity smoke project — repo-relative (same path on macOS & Ubuntu)
_tb3_script_dir() {
  # works in both bash and zsh
  local s="${BASH_SOURCE[0]:-${(%):-%x}}"
  cd "$(dirname "$s")" && pwd
}
export TB3_REPO_ROOT="$(cd "$(_tb3_script_dir)/.." 2>/dev/null && pwd)"
export TB3_UNITY_PROJECT="${TB3_UNITY_PROJECT:-$TB3_REPO_ROOT/unity-smoke}"

# Unity Editor binary candidates — override by exporting TB3_UNITY_BIN
_tb3_unity_default() {
  case "$(uname -s)" in
    Darwin) echo "/Applications/Unity/Hub/Editor/6000.0.64f1/Unity.app/Contents/MacOS/Unity" ;;
    Linux)  for p in \
              "$HOME/Unity/Hub/Editor/6000.0.64f1/Editor/Unity" \
              "/opt/Unity/Editor/Unity" \
              "$(command -v unityhub 2>/dev/null)"; do
              [ -n "$p" ] && [ -x "$p" ] && echo "$p" && return; done; echo "" ;;
    *) echo "" ;;
  esac
}

# ---- OS-portable helpers ----
tb3-myip() {
  case "$(uname -s)" in
    Darwin) ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 ;;
    Linux)  ip -4 -o addr show scope global 2>/dev/null \
            | awk '{print $4}' | cut -d/ -f1 | head -1 ;;
  esac
}

tb3-ip() {
  local hit
  # 0. mDNS (fastest, IP-drift proof) — avahi publishes <TB3_HOSTNAME>.local
  if [ -n "$TB3_HOSTNAME" ]; then
    hit=$(ping -c1 -W1 "${TB3_HOSTNAME}.local" 2>/dev/null \
          | head -1 \
          | grep -oE '([0-9]+\.){3}[0-9]+' \
          | head -1)
    if [ -n "$hit" ]; then
      echo "$hit"
      return 0
    fi
  fi
  # try last known first
  if ping -c1 -W1 "$TB3_ROBOT_IP_HINT" >/dev/null 2>&1; then
    if [ "$(uname -s)" = "Linux" ]; then
      hit=$(ip neigh show "$TB3_ROBOT_IP_HINT" 2>/dev/null \
            | grep -Ei "$TB3_MAC_PATTERN" | awk '{print "'"$TB3_ROBOT_IP_HINT"'"}' | head -1)
    else
      hit=$(arp -an 2>/dev/null | grep -F "($TB3_ROBOT_IP_HINT)" \
            | grep -Ei "$TB3_MAC_PATTERN" | sed -E 's/.*\(([0-9.]+)\).*/\1/' | head -1)
    fi
  fi
  if [ -z "$hit" ]; then
    for i in $(seq 1 254); do
      ping -c 1 -W 1 "${TB3_LAN_CIDR}.${i}" >/dev/null 2>&1 &
    done; wait
    if [ "$(uname -s)" = "Linux" ]; then
      hit=$(ip neigh 2>/dev/null | grep -Ei "$TB3_MAC_PATTERN" | awk '{print $1}' | head -1)
    else
      hit=$(arp -an 2>/dev/null | grep -Ei "$TB3_MAC_PATTERN" \
            | sed -E 's/.*\(([0-9.]+)\).*/\1/' | head -1)
    fi
  fi
  if [ -z "$hit" ]; then
    echo "TurtleBot3 not found on ${TB3_LAN_CIDR}.0/24 (looking for $TB3_MAC_PATTERN)" >&2
    return 1
  fi
  echo "$hit"
}

tb3-ssh() {
  local ip; ip=$(tb3-ip) || return 1
  ssh "$TB3_USER@$ip"
}

tb3-vnc() {
  local ip; ip=$(tb3-ip) || return 1
  echo "vnc://$ip:5902  (password: $TB3_VNC_PASSWORD)"
  case "$(uname -s)" in
    Darwin) open "vnc://$ip:5902" ;;
    Linux)  if command -v xdg-open >/dev/null; then xdg-open "vnc://$ip:5902";
            elif command -v vncviewer >/dev/null; then vncviewer "$ip:5902";
            else echo "Install vinagre/remmina/vncviewer to open VNC"; fi ;;
  esac
}

tb3-port() {
  local ip; ip=$(tb3-ip) || return 1
  nc -vz -G 3 "$ip" 10000 2>&1 || nc -vz -w 3 "$ip" 10000 2>&1
}

tb3-up() {
  # bringup + ros_tcp_endpoint tmux sessions on robot
  local ip mac
  ip=$(tb3-ip) || return 1
  mac=$(tb3-myip) || { echo "cannot detect Mac/Linux LAN IP"; return 1; }
  local script="$TB3_REPO_ROOT/scripts/urhynix_robot_up.sh"
  [ -f "$script" ] || { echo "missing $script"; return 1; }
  echo "→ scp $script to $ip"
  expect <<EXP
set timeout 25
spawn scp -o StrictHostKeyChecking=accept-new $script $TB3_USER@$ip:/tmp/urhynix_robot_up.sh
expect { "password:" { send "$TB3_PASSWORD\r"; exp_continue } eof }
EXP
  echo "→ ssh + run robot_up.sh (Mac/Linux IP = $mac)"
  expect <<EXP
set timeout 25
spawn ssh -o StrictHostKeyChecking=accept-new $TB3_USER@$ip bash /tmp/urhynix_robot_up.sh $mac
expect { "password:" { send "$TB3_PASSWORD\r"; exp_continue } "OK_DONE" { exp_continue } eof }
EXP
}

tb3-down() {
  local ip; ip=$(tb3-ip) || return 1
  expect <<EXP
set timeout 12
spawn ssh -o StrictHostKeyChecking=accept-new $TB3_USER@$ip {bash -lc "tmux kill-session -t bringup 2>/dev/null; tmux kill-session -t ros_tcp 2>/dev/null; tmux kill-session -t rviz 2>/dev/null; tmux kill-session -t arduino_bridge 2>/dev/null; sleep 1; tmux ls 2>/dev/null || echo NO_TMUX"}
expect { "password:" { send "$TB3_PASSWORD\r"; exp_continue } eof }
EXP
}

tb3-bridge() {
  # start Arduino → ROS2 bridge node on robot
  local ip; ip=$(tb3-ip) || return 1
  local script="$TB3_REPO_ROOT/scripts/arduino_bridge.py"
  expect <<EXP
set timeout 15
spawn scp -o StrictHostKeyChecking=accept-new $script $TB3_USER@$ip:/tmp/arduino_bridge.py
expect { "password:" { send "$TB3_PASSWORD\r"; exp_continue } eof }
EXP
  expect <<EXP
set timeout 15
spawn ssh -o StrictHostKeyChecking=accept-new $TB3_USER@$ip {bash -lc "tmux kill-session -t arduino_bridge 2>/dev/null; tmux new-session -d -s arduino_bridge 'bash -lc \"source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET && python3 /tmp/arduino_bridge.py 2>&1 | tee /tmp/arduino_bridge.log\"'; sleep 1; tmux ls"}
expect { "password:" { send "$TB3_PASSWORD\r"; exp_continue } eof }
EXP
}

tb3-arduino() {
  # 8-second raw serial capture (uses udev symlink)
  local ip; ip=$(tb3-ip) || return 1
  expect <<EXP
set timeout 18
spawn ssh -o StrictHostKeyChecking=accept-new $TB3_USER@$ip {bash -lc "python3 - <<'PY'
import serial, time
s = serial.Serial('/dev/tb3_arduino', 9600, timeout=1); time.sleep(2)
deadline = time.time() + 8
while time.time() < deadline:
    line = s.readline().decode('utf-8', errors='replace').strip()
    if line: print('>', line)
s.close()
PY"}
expect { "password:" { send "$TB3_PASSWORD\r"; exp_continue } eof }
EXP
}

tb3-poweroff() {
  local ip; ip=$(tb3-ip) || return 1
  printf "Shutdown robot %s ? (y/N) " "$ip"
  read -r ans
  case "$ans" in y|Y|yes) ;;
    *) echo "abort"; return 0 ;;
  esac
  expect <<EXP
set timeout 10
spawn ssh -o StrictHostKeyChecking=accept-new $TB3_USER@$ip {bash -lc "echo $TB3_PASSWORD | sudo -S shutdown -h now"}
expect { "password:" { send "$TB3_PASSWORD\r"; exp_continue } eof }
EXP
  echo "shutdown issued — verify with: ping -c2 $ip"
}

tb3-slam() {
  # cartographer SLAM tmux 세션 (robot 측). bringup 이미 떠 있어야 함.
  local ip; ip=$(tb3-ip) || return 1
  expect <<EXP
set timeout 18
spawn ssh -o StrictHostKeyChecking=accept-new $TB3_USER@$ip {bash -lc "tmux kill-session -t slam 2>/dev/null; tmux new-session -d -s slam 'bash -lc \"source /opt/ros/jazzy/setup.bash && source \$HOME/turtlebot3_ws/install/setup.bash && export ROS_DOMAIN_ID=210 TURTLEBOT3_MODEL=burger LDS_MODEL=LDS-03 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET && ros2 launch turtlebot3_cartographer cartographer.launch.py use_sim_time:=False 2>&1 | tee /tmp/slam.log\"'; sleep 2; tmux ls"}
expect { "password:" { send "$TB3_PASSWORD\r"; exp_continue } eof }
EXP
  echo "→ /map 토픽 송출까지 5-10s 대기 권장. 검증: ssh kim@$ip 'ros2 topic hz /map'"
}

tb3-slam-save() {
  # 현재 SLAM 맵을 .pgm + .yaml 두 파일로 저장 (robot 측 ~/maps/<name>.*).
  local name="${1:-arena_$(date +%Y%m%d_%H%M%S)}"
  local ip; ip=$(tb3-ip) || return 1
  expect <<EXP
set timeout 25
spawn ssh -o StrictHostKeyChecking=accept-new $TB3_USER@$ip {bash -lc "source /opt/ros/jazzy/setup.bash && export ROS_DOMAIN_ID=210 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET && mkdir -p \$HOME/maps && cd \$HOME/maps && ros2 run nav2_map_server map_saver_cli -f $name --ros-args -p save_map_timeout:=20.0 && ls -la $name.*"}
expect { "password:" { send "$TB3_PASSWORD\r"; exp_continue } eof }
EXP
  echo "→ 로컬로 가져오기: tb3-fetch-map $name"
}

tb3-fetch-map() {
  # robot ~/maps/<name>.{pgm,yaml} → 로컬 docs/evidence/maps/<name>/  (+ PNG 자동 변환)
  local name="${1:?usage: tb3-fetch-map <map_name>}"
  local ip; ip=$(tb3-ip) || return 1
  local outdir="$TB3_REPO_ROOT/docs/evidence/maps/$name"
  mkdir -p "$outdir"
  echo "→ scp ~/maps/$name.{pgm,yaml} → $outdir/"
  # brace expansion이 scp client에서 안 풀리는 환경 대비 — 두 파일 분리.
  scp -o StrictHostKeyChecking=accept-new "$TB3_USER@$ip:maps/$name.pgm" "$outdir/" 2>&1 | tail -1
  scp -o StrictHostKeyChecking=accept-new "$TB3_USER@$ip:maps/$name.yaml" "$outdir/" 2>&1 | tail -1
  # pgm → png 변환 (Unity는 pgm 미지원). ImageMagick 우선, 없으면 PIL.
  if command -v magick >/dev/null 2>&1; then
    magick "$outdir/$name.pgm" "$outdir/$name.png" && echo "→ $name.png (ImageMagick)"
  elif command -v convert >/dev/null 2>&1; then
    convert "$outdir/$name.pgm" "$outdir/$name.png" && echo "→ $name.png (ImageMagick)"
  elif python3 -c "from PIL import Image" >/dev/null 2>&1; then
    python3 -c "from PIL import Image; Image.open('$outdir/$name.pgm').save('$outdir/$name.png')" \
      && echo "→ $name.png (PIL)"
  else
    echo "⚠️ pgm → png 변환 도구 없음 (brew install imagemagick 또는 pip3 install Pillow)"
  fi
  ls -la "$outdir"
}

tb3-map-to-unity() {
  # <name>.png + .yaml을 Unity Assets/Maps/로 복사하고 yaml의 resolution/origin 출력.
  local name="${1:?usage: tb3-map-to-unity <map_name>}"
  local src="$TB3_REPO_ROOT/docs/evidence/maps/$name"
  local dst="$TB3_REPO_ROOT/unity-smoke/Assets/Maps"
  [ -f "$src/$name.png" ] || { echo "missing $src/$name.png (run tb3-fetch-map first)"; return 1; }
  [ -f "$src/$name.yaml" ] || { echo "missing $src/$name.yaml"; return 1; }
  mkdir -p "$dst"
  cp "$src/$name.png" "$src/$name.yaml" "$dst/"
  echo "→ copied to $dst/"
  echo ""
  echo "=== Unity Plane scale 계산 ==="
  python3 - "$src/$name.yaml" "$src/$name.png" <<'PY'
import sys, yaml
from PIL import Image
y = yaml.safe_load(open(sys.argv[1]))
img = Image.open(sys.argv[2])
w, h = img.size
res = float(y.get('resolution', 0.05))
ox, oy, _ = y.get('origin', [0, 0, 0])
mw, mh = w * res, h * res
print(f"이미지: {w} x {h} px")
print(f"resolution: {res} m/px")
print(f"실제 크기: {mw:.2f} m × {mh:.2f} m")
print(f"origin (ROS): x={ox} y={oy}")
print(f"Unity Plane (10u 기본):")
print(f"  scale.x = {mw/10:.4f}")
print(f"  scale.z = {mh/10:.4f}")
print(f"  scale.y = 1")
print(f"Plane 중심을 (0,0,0)에 두고 PNG 텍스처 할당 → top-down 카메라로 확인")
PY
}

tb3-teleop() {
  # 수동 운전. SSH 인터랙티브 — 키보드 입력으로 로봇 움직임.
  # i=전진 j=좌회전 l=우회전 , =후진 k=정지 q/z=속도조절
  local ip; ip=$(tb3-ip) || return 1
  ssh -t "$TB3_USER@$ip" 'bash -lc "source /opt/ros/jazzy/setup.bash && source $HOME/turtlebot3_ws/install/setup.bash && export ROS_DOMAIN_ID=210 TURTLEBOT3_MODEL=burger RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET && ros2 run turtlebot3_teleop teleop_keyboard"'
}

tb3-rviz() {
  # RViz를 로봇 측에서 띄움. VNC로 화면 확인.
  local ip; ip=$(tb3-ip) || return 1
  expect <<EXP
set timeout 12
spawn ssh -o StrictHostKeyChecking=accept-new $TB3_USER@$ip {bash -lc "tmux kill-session -t rviz 2>/dev/null; tmux new-session -d -s rviz 'bash -lc \"source /opt/ros/jazzy/setup.bash && source \$HOME/turtlebot3_ws/install/setup.bash && export DISPLAY=:2 ROS_DOMAIN_ID=210 TURTLEBOT3_MODEL=burger RMW_IMPLEMENTATION=rmw_fastrtps_cpp && rviz2 -d \$HOME/turtlebot3_ws/src/turtlebot3/turtlebot3_cartographer/rviz/tb3_cartographer.rviz 2>&1 | tee /tmp/rviz.log\"'; sleep 1; tmux ls"}
expect { "password:" { send "$TB3_PASSWORD\r"; exp_continue } eof }
EXP
  echo "→ tb3-vnc 로 화면 확인 (:2)"
}

tb3-nav2() {
  # Nav2 stack 시작. <map_name>.yaml (robot의 ~/maps/) 기반 localization + 1-waypoint.
  local map="${1:?usage: tb3-nav2 <map_name (~/maps/<name>.yaml)>}"
  local ip; ip=$(tb3-ip) || return 1
  expect <<EXP
set timeout 18
spawn ssh -o StrictHostKeyChecking=accept-new $TB3_USER@$ip {bash -lc "tmux kill-session -t nav2 2>/dev/null; tmux new-session -d -s nav2 'bash -lc \"source /opt/ros/jazzy/setup.bash && source \$HOME/turtlebot3_ws/install/setup.bash && export ROS_DOMAIN_ID=210 TURTLEBOT3_MODEL=burger LDS_MODEL=LDS-03 RMW_IMPLEMENTATION=rmw_fastrtps_cpp ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET && ros2 launch turtlebot3_navigation2 navigation2.launch.py use_sim_time:=False map:=\$HOME/maps/$map.yaml 2>&1 | tee /tmp/nav2.log\"'; sleep 2; tmux ls"}
expect { "password:" { send "$TB3_PASSWORD\r"; exp_continue } eof }
EXP
  echo "→ RViz에서 2D Pose Estimate(초기 위치) + Nav2 Goal(목표) 클릭. 검증: ros2 topic echo /amcl_pose --once"
}

tb3-pkg-check() {
  # 로봇에 SLAM/Nav2 필수 패키지 4종 존재 여부. SSH key 인증 후에는 expect 불필요.
  local ip; ip=$(tb3-ip) || return 1
  ssh -o BatchMode=yes -o ConnectTimeout=6 "$TB3_USER@$ip" \
    "dpkg -l | grep -E 'ros-jazzy-(turtlebot3-cartographer|turtlebot3-navigation2|nav2-map-server|teleop-twist-keyboard)' | awk '{print \$2}'" 2>&1
}

tb3-pkg-install() {
  # 누락된 SLAM/Nav2 패키지 설치 (sudo 비번 자동).
  local ip; ip=$(tb3-ip) || return 1
  ssh -t "$TB3_USER@$ip" "echo $TB3_PASSWORD | sudo -S apt update && echo $TB3_PASSWORD | sudo -S apt install -y ros-jazzy-turtlebot3-cartographer ros-jazzy-turtlebot3-navigation2 ros-jazzy-nav2-map-server ros-jazzy-teleop-twist-keyboard"
}

tb3-disk-cleanup() {
  # apt cache + 오래된 로그 + 워크스페이스 빌드 잔재 정리 (apt 작업 완료 후에만 실행).
  local ip; ip=$(tb3-ip) || return 1
  echo "→ before:"; ssh -o BatchMode=yes "$TB3_USER@$ip" "df -h / | tail -1"
  ssh -t "$TB3_USER@$ip" "
    echo $TB3_PASSWORD | sudo -S apt clean
    echo $TB3_PASSWORD | sudo -S journalctl --vacuum-size=50M
    echo $TB3_PASSWORD | sudo -S apt autoremove -y
    rm -rf ~/.cache/pip ~/.cache/colcon 2>/dev/null
  "
  echo "→ after:"; ssh -o BatchMode=yes "$TB3_USER@$ip" "df -h / | tail -1"
}

tb3-disk() {
  # 디스크 한 줄 요약.
  local ip; ip=$(tb3-ip) || return 1
  ssh -o BatchMode=yes "$TB3_USER@$ip" "df -h / | tail -1"
}

# ───────── Mac Docker ROS2 SLAM helpers ─────────
# 라즈베리파이 디스크 회피 — cartographer/nav2를 Mac 컨테이너에서 실행.
# 전제: Docker Desktop 4.34+ + Settings > Resources > Network > Enable host networking ON.
# 자세히: docs/ref/MAC-DOCKER-ROS2-PLAYBOOK.md
export TB3_DOCKER_IMAGE="${TB3_DOCKER_IMAGE:-robotis/turtlebot3:jazzy-pc-latest}"
export TB3_DOCKER_NAME="${TB3_DOCKER_NAME:-urhynix_slam}"

tb3-docker-pull() {
  # 5GB pull (1회용). 캐시 후 즉시.
  docker pull --platform linux/arm64 "$TB3_DOCKER_IMAGE"
}

_tb3_docker_env() {
  # 공통 env 인자 출력.
  local robot_ip; robot_ip=$(tb3-ip 2>/dev/null) || robot_ip="$TB3_ROBOT_IP_HINT"
  printf -- '-e ROS_DOMAIN_ID=210 -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp -e ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET -e ROS_STATIC_PEERS=%s -e TURTLEBOT3_MODEL=burger' "$robot_ip"
}

tb3-docker-shell() {
  # 인터랙티브 bash 진입 (디버깅·검증·맵 저장 수동 작업).
  # shellcheck disable=SC2046
  docker run --rm -it \
    --network host \
    $(_tb3_docker_env) \
    -v "$TB3_REPO_ROOT/docs/evidence/maps:/maps" \
    "$TB3_DOCKER_IMAGE" \
    bash -c "source /opt/ros/jazzy/setup.bash 2>/dev/null; [ -f /opt/turtlebot3_ws/install/setup.bash ] && source /opt/turtlebot3_ws/install/setup.bash; cd /maps; exec bash"
}

tb3-docker-topics() {
  # 호스트에서 robot 토픽 발견 확인 (DDS 통신 검증).
  # shellcheck disable=SC2046
  docker run --rm \
    --network host \
    $(_tb3_docker_env) \
    "$TB3_DOCKER_IMAGE" \
    bash -c "source /opt/ros/jazzy/setup.bash && timeout 6 ros2 topic list 2>&1 | sort"
}

tb3-docker-slam() {
  # detached 컨테이너로 cartographer launch.
  docker rm -f "$TB3_DOCKER_NAME" 2>/dev/null
  # shellcheck disable=SC2046
  docker run -d --name "$TB3_DOCKER_NAME" \
    --network host \
    $(_tb3_docker_env) \
    -v "$TB3_REPO_ROOT/docs/evidence/maps:/maps" \
    "$TB3_DOCKER_IMAGE" \
    bash -c "source /opt/ros/jazzy/setup.bash && ros2 launch turtlebot3_cartographer cartographer.launch.py use_sim_time:=False"
  echo "→ container: $TB3_DOCKER_NAME"
  echo "→ 로그 보기: docker logs -f $TB3_DOCKER_NAME"
  echo "→ /map 송출까지 5-10s 대기 권장. 검증: tb3-docker-mhz"
}

tb3-docker-mhz() {
  # /map 토픽 hz (cartographer 살아있나).
  docker exec "$TB3_DOCKER_NAME" bash -c "source /opt/ros/jazzy/setup.bash && timeout 6 ros2 topic hz /map 2>&1 | tail -5"
}

tb3-docker-save() {
  # 현재 SLAM 맵을 host의 docs/evidence/maps/<name>/<name>.{pgm,yaml}로 저장.
  local name="${1:?usage: tb3-docker-save <map_name>}"
  local outdir="$TB3_REPO_ROOT/docs/evidence/maps/$name"
  mkdir -p "$outdir"
  docker exec "$TB3_DOCKER_NAME" bash -c "
    source /opt/ros/jazzy/setup.bash
    cd /maps/$name 2>/dev/null || mkdir -p /maps/$name && cd /maps/$name
    ros2 run nav2_map_server map_saver_cli -f $name --ros-args -p save_map_timeout:=20.0
    ls -la $name.*
  "
  # pgm → png 변환 (호스트에서)
  if command -v magick >/dev/null 2>&1; then
    magick "$outdir/$name.pgm" "$outdir/$name.png" && echo "→ $name.png (ImageMagick)"
  elif python3 -c "from PIL import Image" >/dev/null 2>&1; then
    python3 -c "from PIL import Image; Image.open('$outdir/$name.pgm').save('$outdir/$name.png')" \
      && echo "→ $name.png (PIL)"
  fi
  ls -la "$outdir"
}

tb3-docker-stop() {
  # 컨테이너 정리.
  docker stop "$TB3_DOCKER_NAME" 2>/dev/null
  docker rm "$TB3_DOCKER_NAME" 2>/dev/null
  echo "→ stopped + removed: $TB3_DOCKER_NAME"
}

tb3-docker-logs() {
  docker logs -f --tail 30 "$TB3_DOCKER_NAME"
}

tb3-unity() {
  local bin="${TB3_UNITY_BIN:-$(_tb3_unity_default)}"
  if [ -z "$bin" ] || [ ! -x "$bin" ]; then
    echo "Unity Editor not found. Install Unity Hub + 6000.0.64f1, or export TB3_UNITY_BIN=/path/to/Unity" >&2
    return 1
  fi
  case "$(uname -s)" in
    Darwin) open -na "/Applications/Unity/Hub/Editor/6000.0.64f1/Unity.app" --args \
              -projectPath "$TB3_UNITY_PROJECT" \
              -executeMethod RosSmokeConfigure.Play \
              -logFile /tmp/unity-tb3-smoke.log ;;
    Linux)  "$bin" -projectPath "$TB3_UNITY_PROJECT" \
              -executeMethod RosSmokeConfigure.Play \
              -logFile /tmp/unity-tb3-smoke.log & disown ;;
  esac
  echo "Unity launching → log: /tmp/unity-tb3-smoke.log"
}

tb3-key-setup() {
  # 한 번만 실행: Mac/Linux ed25519 공개키를 로봇에 등록 → 이후 비번 prompt 사라짐
  local ip; ip=$(tb3-ip) || return 1
  if [ ! -f "$HOME/.ssh/id_ed25519.pub" ]; then
    echo "→ generating new ed25519 key (no passphrase)"
    ssh-keygen -t ed25519 -N '' -f "$HOME/.ssh/id_ed25519" || return $?
  fi
  echo "→ ssh-copy-id to $TB3_USER@$ip (will prompt for robot password once)"
  expect <<EXP
set timeout 30
spawn ssh-copy-id -i $HOME/.ssh/id_ed25519.pub -o StrictHostKeyChecking=accept-new -o PreferredAuthentications=password -o PubkeyAuthentication=no $TB3_USER@$ip
expect {
  "password:" { send "$TB3_PASSWORD\r"; exp_continue }
  timeout { exit 2 }
  eof
}
EXP
  echo "→ verify passwordless login"
  ssh -o BatchMode=yes -o ConnectTimeout=6 "$TB3_USER@$ip" 'echo "OK from $(hostname)"' 2>&1 | head -3
}

tb3-go() {
  # 한 방 풀-기동: bringup + ros_tcp + arduino_bridge + 검증
  echo "▶ tb3-up (bringup + ros_tcp_endpoint)"
  tb3-up || return $?
  echo "▶ wait 12s for ros_tcp listen..."
  sleep 12
  echo "▶ tb3-bridge (arduino → ROS2 + Supabase)"
  tb3-bridge
  echo "▶ verify TCP 10000"
  tb3-port
}

tb3-restart() {
  echo "▶ tb3-down"
  tb3-down
  tb3-go
}

tb3-logs() {
  # 양쪽 tmux 로그 + 세션 한 화면
  local ip; ip=$(tb3-ip) || return 1
  expect <<EXP
set timeout 15
spawn ssh -o StrictHostKeyChecking=accept-new $TB3_USER@$ip {bash -lc "echo --TMUX--; tmux ls 2>/dev/null || echo NO_TMUX; echo; echo --BRINGUP--; tail -15 /tmp/bringup.log 2>/dev/null; echo; echo --ROS_TCP--; tail -15 /tmp/ros_tcp_endpoint.log 2>/dev/null; echo; echo --BRIDGE--; tail -15 /tmp/arduino_bridge.log 2>/dev/null"}
expect {
  "password:" { send "$TB3_PASSWORD\r"; exp_continue }
  eof
}
EXP
}

tb3-help() {
  cat <<EOF
URHYNIX TurtleBot helpers ($(uname -s))

  tb3-myip       Local LAN IP of this machine
  tb3-ip         Find robot IP by MAC pattern $TB3_MAC_PATTERN
  tb3-ssh        SSH into robot ($TB3_USER@<ip>)
  tb3-vnc        Open VNC viewer (RViz at :2)
  tb3-port       Check ROS-TCP port 10000

  tb3-up         Start bringup + ros_tcp_endpoint tmux on robot
  tb3-down       Kill all robot ROS tmux sessions
  tb3-bridge     Start Arduino → ROS2 bridge node on robot
  tb3-arduino    8-sec raw serial capture from /dev/tb3_arduino
  tb3-poweroff   sudo shutdown -h now (asks for confirmation)

  tb3-go         ★ up + wait + bridge + verify (one-shot full boot)
  tb3-restart    ★ down + go (clean restart)
  tb3-logs       Tail bringup/ros_tcp/arduino_bridge logs + tmux ls
  tb3-key-setup  ★ ssh-copy-id 한 번 (이후 비번 prompt 영구 사라짐)

  tb3-pkg-check     SLAM/Nav2 4개 패키지 존재 여부 확인
  tb3-pkg-install   누락된 SLAM/Nav2 패키지 4종 일괄 apt install
  tb3-disk          로봇 SD 카드 사용량 한 줄
  tb3-disk-cleanup  apt cache + 로그 + 빌드 잔재 정리 (≈1GB 회복)

  ── Mac Docker SLAM (라즈베리파이 디스크 회피) ──
  tb3-docker-pull   robotis/turtlebot3:jazzy-pc-latest 5GB pull (1회)
  tb3-docker-topics 호스트에서 robot 토픽 발견 검증 (DDS 통신)
  tb3-docker-shell  컨테이너 인터랙티브 bash (디버깅·수동작업)
  tb3-docker-slam   detached cartographer launch
  tb3-docker-mhz    /map 토픽 hz 측정 (cartographer 검증)
  tb3-docker-save N 현재 맵 저장 → docs/evidence/maps/<N>/{.pgm,.yaml,.png}
  tb3-docker-logs   컨테이너 로그 tail -f
  tb3-docker-stop   컨테이너 종료 + 정리
  tb3-slam         cartographer SLAM tmux 시작 (/map 토픽 송출)
  tb3-rviz         로봇 RViz (tb3-vnc로 화면 확인)
  tb3-teleop       수동 운전 (i/j/k/l/, 키보드)
  tb3-slam-save N    현재 맵 저장 ~/maps/<N>.{pgm,yaml}
  tb3-fetch-map N    맵 파일 → docs/evidence/maps/<N>/ + PNG 자동 변환
  tb3-map-to-unity N PNG+yaml → unity-smoke/Assets/Maps/ + Plane scale 계산
  tb3-nav2 N         Nav2 stack 시작 (map=<N>.yaml, RViz에서 goal 클릭)

  tb3-unity      Launch Unity Editor on $TB3_UNITY_PROJECT (auto-Play)

Env overrides: TB3_USER, TB3_PASSWORD, TB3_ROBOT_IP_HINT, TB3_LAN_CIDR,
               TB3_UNITY_PROJECT, TB3_UNITY_BIN

Additional URHYNIX aliases: run \`urhynix-help\`
EOF
}

# ─────── auto-load URHYNIX aliases (urhynix-*, sb-*) ───────
[ -f "$TB3_REPO_ROOT/scripts/aliases.sh" ] && . "$TB3_REPO_ROOT/scripts/aliases.sh"
