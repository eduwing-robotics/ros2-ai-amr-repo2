#!/usr/bin/env bash
# Gen.G ArUco viewer — Gen.G detector UI (boxes / axes / status).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROBOT=geng
# shellcheck source=/dev/null
source "${ROOT}/scripts/env.sh"
exec python3 "${ROOT}/scripts/aruco_dock_detector.py" --robot geng --scale "${SCALE:-2.0}" "$@"
