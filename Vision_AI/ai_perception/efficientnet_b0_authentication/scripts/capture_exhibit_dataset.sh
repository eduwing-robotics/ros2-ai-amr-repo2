#!/usr/bin/env bash
# Exhibit authenticity dataset capture (Phase 1) — laptop helper.
# Sources camera_laptop_env.sh then runs capture_exhibit_dataset.py.
#
# Usage:
#   ./ai_perception/efficientnet_b0_authentication/scripts/capture_exhibit_dataset.sh preview
#   ./ai_perception/efficientnet_b0_authentication/scripts/capture_exhibit_dataset.sh preview --roi 100 80 320 220
#   ./ai_perception/efficientnet_b0_authentication/scripts/capture_exhibit_dataset.sh snap --roi 100 80 320 220
#   ./ai_perception/efficientnet_b0_authentication/scripts/capture_exhibit_dataset.sh capture --label genuine --session session_01 --count 5 --interval 0.4
#   ./ai_perception/efficientnet_b0_authentication/scripts/capture_exhibit_dataset.sh capture --label fake_01 --session session_01 --count 5 --roi 100 80 320 220
# If preview window does not appear: use OS terminal (not Cursor), or use snap.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
# shellcheck source=/dev/null
source "${ROOT}/scripts/camera_laptop_env.sh"

if [[ $# -lt 1 ]]; then
  echo "usage: $0 preview|capture [args...]"
  echo "  see: python3 ${ROOT}/ai_perception/efficientnet_b0_authentication/scripts/capture_exhibit_dataset.py --help"
  exit 1
fi

exec python3 "${ROOT}/ai_perception/efficientnet_b0_authentication/scripts/capture_exhibit_dataset.py" "$@"
