#!/usr/bin/env bash
# 로봇 ↔ 노트북 ROS 2 멀티머신 (Wi-Fi 영상 + 팀 FastDDS 정렬)
#
# DDS 요약:
#   FastDDS (기본) — 팀 URHYNIX 표준. 멀티캐스트 + initialPeers(로봇·노트북 IP).
#   CycloneDDS+peers — USE_CYCLONEDDS=1 일 때만. Wi-Fi에서 discovery가 안 될 때 대안.
#
# 수동 사용:
#   export ROS_DOMAIN_ID=2   # T1. Gen.G 매핑은 1 (scripts/genji_mapping_env.sh)
#   export LAPTOP_IP=<노트북 IP>   # 로봇 SSH에서 카메라 띄울 때 필수
#   source scripts/ros_multimachine_env.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-2}"
export USE_CYCLONEDDS="${USE_CYCLONEDDS:-0}"
# bashrc가 LOCALHOST를 export해도 Cyclone은 무조건 OFF (:- 기본값은 LOCALHOST를 보존함)
if [[ "${USE_CYCLONEDDS}" == "1" ]]; then
  export ROS_AUTOMATIC_DISCOVERY_RANGE=OFF
else
  export ROS_AUTOMATIC_DISCOVERY_RANGE="${ROS_AUTOMATIC_DISCOVERY_RANGE:-SUBNET}"
fi
export ROS_LOCALHOST_ONLY=0

export ROBOT_NS="${ROBOT_NS:-tb3_1}"
export T1_CAMERA_RAW="/${ROBOT_NS}/camera/color/image_raw"
export T1_CAMERA_COMPRESSED="/${ROBOT_NS}/camera/color/image_raw/compressed"

export ROBOT_IP="${ROBOT_IP:-192.168.20.101}"
export LAPTOP_IP_DEFAULT="${LAPTOP_IP_DEFAULT:-}"
LOCAL_IP="$(ip -4 addr show scope global 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1 | head -1)"

_is_robot_host() {
  [[ -n "${LOCAL_IP}" && "${LOCAL_IP}" == "${ROBOT_IP}" ]]
}

_laptop_ip_from_ssh() {
  # SSH_CLIENT / SSH_CONNECTION: "<client_ip> <client_port> ..."
  if [[ -n "${SSH_CLIENT:-}" ]]; then
    echo "${SSH_CLIENT%% *}"
    return 0
  fi
  if [[ -n "${SSH_CONNECTION:-}" ]]; then
    echo "${SSH_CONNECTION%% *}"
    return 0
  fi
  return 1
}

_is_bad_laptop_ip() {
  [[ -z "${1:-}" || "${1}" == "127.0.0.1" || "${1}" == "::1" ]]
}

if _is_robot_host; then
  if [[ -z "${LAPTOP_IP:-}" ]]; then
    if _ssh_ip="$(_laptop_ip_from_ssh)"; then
      LAPTOP_IP="${_ssh_ip}"
    elif [[ -n "${LAPTOP_IP_DEFAULT:-}" ]]; then
      LAPTOP_IP="${LAPTOP_IP_DEFAULT}"
    fi
    export LAPTOP_IP
  fi
  if _is_bad_laptop_ip "${LAPTOP_IP:-}"; then
    # Cyclone은 discovery=OFF + static peers — 127.0.0.1 peer면 노트북에 토픽이 안 보임
    if [[ "${USE_CYCLONEDDS:-0}" == "1" ]]; then
      echo "[ERROR] Robot — LAPTOP_IP required for CycloneDDS (discovery OFF; refuse 127.0.0.1 peers)." >&2
      echo "  export LAPTOP_IP=<laptop IP>  (e.g. 192.168.20.4)" >&2
      echo "  or launch via SSH so SSH_CLIENT is set automatically." >&2
      return 1 2>/dev/null || exit 1
    fi
    echo "[WARN] Robot — LAPTOP_IP 미설정. export LAPTOP_IP=<노트북IP> 권장 (127.0.0.1 사용 안 함)" >&2
  else
    echo "[INFO] Robot — laptop peer ${LAPTOP_IP} (export LAPTOP_IP=... if wrong)" >&2
  fi
else
  if [[ -z "${LAPTOP_IP:-}" ]]; then
    LAPTOP_IP="$(ip -4 route get "${ROBOT_IP}" 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1); exit}')"
    export LAPTOP_IP
  fi
fi

if _is_bad_laptop_ip "${LAPTOP_IP:-}" && [[ "${USE_CYCLONEDDS:-0}" == "1" ]]; then
  echo "[ERROR] LAPTOP_IP unset/invalid with USE_CYCLONEDDS=1 — refusing 127.0.0.1 Cyclone peers." >&2
  echo "  export LAPTOP_IP=<laptop IP>" >&2
  return 1 2>/dev/null || exit 1
fi

export ROS_STATIC_PEERS="${ROBOT_IP};${LAPTOP_IP};127.0.0.1"

_use_cyclone() {
  [[ -f /opt/ros/jazzy/lib/librmw_cyclonedds_cpp.so ]]
}

# Cyclone: Wi-Fi 카메라용. discovery=OFF + CYCLONEDDS_URI peers XML은 이 LAN에서
# 토픽이 안 보이는 경우가 있어 SUBNET 멀티캐스트를 쓴다 (실측 hz~30).
# bashrc LOCALHOST는 무조건 덮어쓴다.
if [[ "${USE_CYCLONEDDS:-0}" == "1" ]] && _use_cyclone; then
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
  unset ROS_LOCALHOST_ONLY
  unset CYCLONEDDS_URI
  unset FASTRTPS_DEFAULT_PROFILES_FILE FASTDDS_DEFAULT_PROFILES_FILE
  echo "[OK] RMW=cyclonedds peers=${ROBOT_IP},${LAPTOP_IP} discovery=${ROS_AUTOMATIC_DISCOVERY_RANGE}" >&2
else
  export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
  _FAST_XML="$(mktemp /tmp/fastdds_peers_XXXXXX.xml)"
  cat > "${_FAST_XML}" <<EOF
<?xml version="1.0" encoding="UTF-8" ?>
<profiles xmlns="http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles">
  <participant profile_name="default" is_default_profile="true">
    <rtps>
      <builtin>
        <discovery_config>
          <discoveryProtocol>SIMPLE</discoveryProtocol>
        </discovery_config>
        <initialPeersList>
          <locator><udpv4><address>${ROBOT_IP}</address></udpv4></locator>
          <locator><udpv4><address>${LAPTOP_IP}</address></udpv4></locator>
        </initialPeersList>
      </builtin>
    </rtps>
  </participant>
</profiles>
EOF
  export FASTRTPS_DEFAULT_PROFILES_FILE="${_FAST_XML}"
  export FASTDDS_DEFAULT_PROFILES_FILE="${_FAST_XML}"
  unset CYCLONEDDS_URI
  echo "[OK] RMW=fastrtps peers=${ROBOT_IP},${LAPTOP_IP} (USE_CYCLONEDDS=1 for cyclone)" >&2
fi

echo "[OK] multimachine DOMAIN_ID=${ROS_DOMAIN_ID} ns=${ROBOT_NS} robot=${ROBOT_IP} laptop=${LAPTOP_IP}" >&2
echo "[OK] camera topic: ${T1_CAMERA_COMPRESSED}" >&2

if [[ "${LAPTOP_IP}" == 192.168.0.* ]] && [[ "${ROBOT_IP}" == 192.168.20.* ]]; then
  echo "[WARN] 다른 Wi-Fi 대역 — 영상이 안 올 수 있습니다." >&2
fi
