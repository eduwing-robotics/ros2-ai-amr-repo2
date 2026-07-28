#!/usr/bin/env bash
# Phase 2 — session-based train/val/test split for painting authenticity.
# Thin wrapper around prepare_auth_dataset.py (no ROS env needed).
#
# Usage:
#   ./ai_perception/efficientnet_b0_authentication/scripts/prepare_auth_dataset.sh --auto --force
#   ./ai_perception/efficientnet_b0_authentication/scripts/prepare_auth_dataset.sh \
#     --train-sessions session_01,session_02,session_03 \
#     --val-sessions session_04 \
#     --test-sessions session_05 \
#     --force
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
exec python3 "${ROOT}/ai_perception/efficientnet_b0_authentication/scripts/prepare_auth_dataset.py" "$@"
