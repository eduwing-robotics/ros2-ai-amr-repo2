#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROBOT="${ROBOT:-geng}"
source "${ROOT}/scripts/env.sh"

exec python3 "${ROOT}/scripts/save_current_waypoint.py" "$@"
