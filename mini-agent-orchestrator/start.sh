#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

MODEL="${MODEL:-qwen3.5:2b}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
APP_HOST="${APP_HOST:-0.0.0.0}"
APP_PORT="${APP_PORT:-8000}"
APP_PORT_SEARCH_LIMIT="${APP_PORT_SEARCH_LIMIT:-20}"
LOG_LEVEL="${LOG_LEVEL:-info}"
OLLAMA_RETRIES="${OLLAMA_RETRIES:-10}"
OLLAMA_RETRY_DELAY="${OLLAMA_RETRY_DELAY:-2}"
CURL_CONNECT_TIMEOUT="${CURL_CONNECT_TIMEOUT:-3}"
CURL_MAX_TIME="${CURL_MAX_TIME:-20}"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

port_in_use() {
  local port="$1"
  lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
}

is_app_healthy_on_port() {
  local port="$1"
  local openapi
  local root_status

  openapi=$(curl -fsS \
    --connect-timeout "${CURL_CONNECT_TIMEOUT}" \
    --max-time "${CURL_MAX_TIME}" \
    "http://127.0.0.1:${port}/openapi.json" 2>/dev/null || true)

  root_status=$(curl -sS \
    --connect-timeout "${CURL_CONNECT_TIMEOUT}" \
    --max-time "${CURL_MAX_TIME}" \
    -o /dev/null \
    -w "%{http_code}" \
    "http://127.0.0.1:${port}/" 2>/dev/null || true)

  [[ "${openapi}" == *'"title":"mini-agent-orchestrator"'* && "${root_status}" == "200" ]]
}

select_port() {
  local candidate="${APP_PORT}"
  local attempts=0

  while port_in_use "${candidate}"; do
    if is_app_healthy_on_port "${candidate}"; then
      log "App already running on http://127.0.0.1:${candidate}"
      return 1
    fi

    attempts=$((attempts + 1))
    if [[ "${attempts}" -ge "${APP_PORT_SEARCH_LIMIT}" ]]; then
      log "No free port found starting from ${APP_PORT} after ${APP_PORT_SEARCH_LIMIT} attempts"
      return 2
    fi

    candidate=$((candidate + 1))
  done

  APP_PORT="${candidate}"
  return 0
}

resolve_runner() {
  if command -v uv >/dev/null 2>&1; then
    echo "uv run uvicorn"
    return 0
  fi

  if [[ -x "${SCRIPT_DIR}/.venv/bin/uv" ]]; then
    echo "${SCRIPT_DIR}/.venv/bin/uv run uvicorn"
    return 0
  fi

  if [[ -x "${SCRIPT_DIR}/.venv/bin/python" ]]; then
    if "${SCRIPT_DIR}/.venv/bin/python" -m uv --version >/dev/null 2>&1; then
      echo "${SCRIPT_DIR}/.venv/bin/python -m uv run uvicorn"
      return 0
    fi
  fi

  if [[ -x "${SCRIPT_DIR}/.venv/bin/uvicorn" ]]; then
    echo "${SCRIPT_DIR}/.venv/bin/uvicorn"
    return 0
  fi

  if [[ -x "${SCRIPT_DIR}/.venv/bin/python" ]]; then
    echo "${SCRIPT_DIR}/.venv/bin/python -m uvicorn"
    return 0
  fi

  if command -v uvicorn >/dev/null 2>&1; then
    echo "uvicorn"
    return 0
  fi

  return 1
}

is_ollama_healthy() {
  curl -fsS \
    --connect-timeout "${CURL_CONNECT_TIMEOUT}" \
    --max-time "${CURL_MAX_TIME}" \
    "${OLLAMA_URL}/api/tags" >/dev/null 2>&1
}

wait_for_ollama() {
  local attempts=0
  until is_ollama_healthy; do
    attempts=$((attempts + 1))
    if [[ "${attempts}" -ge "${OLLAMA_RETRIES}" ]]; then
      log "Ollama did not become ready after ${OLLAMA_RETRIES} attempts"
      return 1
    fi
    log "Waiting for Ollama (${attempts}/${OLLAMA_RETRIES})"
    sleep "${OLLAMA_RETRY_DELAY}"
  done
  return 0
}

ensure_ollama_running() {
  if is_ollama_healthy; then
    log "Ollama is already running"
    return 0
  fi

  if ! command -v ollama >/dev/null 2>&1; then
    log "Ollama CLI not found. Install Ollama first: https://ollama.com"
    return 1
  fi

  log "Starting Ollama service"
  nohup ollama serve > logs/ollama.log 2>&1 &

  wait_for_ollama
}

ensure_model_present() {
  if ollama list | awk '{print $1}' | grep -Fxq "${MODEL}"; then
    log "Model ${MODEL} is already available"
    return 0
  fi

  log "Pulling model ${MODEL}"
  ollama pull "${MODEL}"
}

verify_llm_api() {
  local payload
  payload=$(cat <<EOF
{"model":"${MODEL}"}
EOF
)

  local attempts=0
  until curl -fsS "${OLLAMA_URL}/api/show" \
    --connect-timeout "${CURL_CONNECT_TIMEOUT}" \
    --max-time "${CURL_MAX_TIME}" \
    -H 'Content-Type: application/json' \
    -d "${payload}" >/dev/null 2>&1; do
    attempts=$((attempts + 1))
    if [[ "${attempts}" -ge "${OLLAMA_RETRIES}" ]]; then
      log "Ollama model API is not healthy"
      return 1
    fi
    log "Retrying Ollama model API health (${attempts}/${OLLAMA_RETRIES})"
    sleep "${OLLAMA_RETRY_DELAY}"
  done

  log "Ollama model API is healthy"
}

main() {
  mkdir -p logs

  ensure_ollama_running
  ensure_model_present
  verify_llm_api

  if select_port; then
    :
  else
    local port_status=$?
    if [[ "${port_status}" -eq 1 ]]; then
      return 0
    fi
    return 1
  fi

  log "Starting FastAPI server on ${APP_HOST}:${APP_PORT}"

  local runner
  if runner="$(resolve_runner)"; then
    exec ${runner} app.main:app --host "${APP_HOST}" --port "${APP_PORT}" --log-level "${LOG_LEVEL}"
  fi

  log "No compatible runner found. Install dependencies with: uv sync --extra dev"
  return 1
}

main
