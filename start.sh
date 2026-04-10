#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_SCRIPT="${SCRIPT_DIR}/mini-agent-orchestrator/start.sh"

if [[ ! -f "${TARGET_SCRIPT}" ]]; then
  echo "Error: expected launcher not found at ${TARGET_SCRIPT}" >&2
  exit 1
fi

exec bash "${TARGET_SCRIPT}" "$@"
