#!/bin/bash
# setup.sh - First-run setup for MediSprache (local mode)
# Supports provider choice: ollama or gemini.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ENV_FILE=".env"
AGENT_ENV_FILE="backend/medisprache/.env"
FIXED_OLLAMA_MODEL="qwen2.5:1.5b"
FIXED_GEMINI_MODEL="gemini-3-flash-preview"
DEFAULT_OLLAMA_API_BASE="http://ollama:11434"
TEMP_DOCKER_CONFIG_DIR=""

cleanup_temp_docker_config() {
  if [[ -z "${TEMP_DOCKER_CONFIG_DIR:-}" ]]; then
    return 0
  fi

  if [[ -d "$TEMP_DOCKER_CONFIG_DIR" && "$TEMP_DOCKER_CONFIG_DIR" == /tmp/* ]]; then
    rm -rf "$TEMP_DOCKER_CONFIG_DIR"
  fi
}

trap cleanup_temp_docker_config EXIT

get_env_file_value() {
  local key="$1"
  local env_file="${2:-$ENV_FILE}"
  local line=""
  [[ -f "$env_file" ]] || return 0
  line="$(grep -E "^${key}=" "$env_file" | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    return 0
  fi
  printf "%s" "${line#*=}"
}

upsert_env_value() {
  local key="$1"
  local value="$2"
  local env_file="${3:-$ENV_FILE}"
  local tmp_file

  tmp_file="$(mktemp)"
  if [[ -f "$env_file" ]]; then
    awk -v key="$key" -v value="$value" -F= '
      BEGIN { updated = 0 }
      $1 == key { print key "=" value; updated = 1; next }
      { print }
      END { if (!updated) print key "=" value }
    ' "$env_file" > "$tmp_file"
  else
    printf "%s=%s\n" "$key" "$value" > "$tmp_file"
  fi

  mv "$tmp_file" "$env_file"
}

delete_env_key() {
  local key="$1"
  local env_file="${2:-$ENV_FILE}"
  local tmp_file

  [[ -f "$env_file" ]] || return 0
  tmp_file="$(mktemp)"
  awk -v key="$key" -F= '$1 != key { print }' "$env_file" > "$tmp_file"
  mv "$tmp_file" "$env_file"
}

sync_agent_env_file() {
  local keys key value
  mkdir -p "$(dirname "$AGENT_ENV_FILE")"
  touch "$AGENT_ENV_FILE"

  keys=(
    "LLM_PROVIDER"
    "OLLAMA_API_BASE"
    "GOOGLE_API_KEY"
    "GEMINI_API_KEY"
    "GOOGLE_GENAI_USE_VERTEXAI"
  )

  for key in "${keys[@]}"; do
    value="$(get_env_file_value "$key" "$ENV_FILE")"
    if [[ -n "$value" ]]; then
      upsert_env_value "$key" "$value" "$AGENT_ENV_FILE"
    else
      delete_env_key "$key" "$AGENT_ENV_FILE"
    fi
  done
}

normalize_provider() {
  printf "%s" "$1" | tr '[:upper:]' '[:lower:]' | xargs
}

prompt_provider() {
  local provider_input=""
  while true; do
    read -r -p "Choose LLM provider [ollama/gemini]: " provider_input
    provider_input="$(normalize_provider "$provider_input")"
    if [[ "$provider_input" == "ollama" || "$provider_input" == "gemini" ]]; then
      printf "%s" "$provider_input"
      return 0
    fi
    echo "  [FAIL] Invalid provider. Enter 'ollama' or 'gemini'."
  done
}

is_wsl() {
  grep -qiE "(microsoft|wsl)" /proc/version 2>/dev/null
}

prepare_wsl_docker_config() {
  if ! is_wsl; then
    return 0
  fi

  local docker_config_root="${DOCKER_CONFIG:-$HOME/.docker}"
  local docker_config_file="$docker_config_root/config.json"

  [[ -f "$docker_config_file" ]] || return 0

  if ! grep -qiE '"credsStore"[[:space:]]*:[[:space:]]*".*desktop' "$docker_config_file"; then
    return 0
  fi

  TEMP_DOCKER_CONFIG_DIR="$(mktemp -d)"
  export DOCKER_CONFIG="$TEMP_DOCKER_CONFIG_DIR"
  mkdir -p "$DOCKER_CONFIG"
  printf "{}\n" > "$DOCKER_CONFIG/config.json"

  echo "  [WARN] WSL detected with desktop credential helper in Docker config."
  echo "         Using temporary DOCKER_CONFIG=$DOCKER_CONFIG for this setup run."
}

cleanup_stale_ollama_containers() {
  # `docker compose down` without `--profile ollama` leaves profiled containers.
  # If the project network is removed, those containers can retain a stale
  # network reference and fail to start with "network ... not found".
  docker compose --profile ollama rm -fsv ollama ollama-init >/dev/null 2>&1 || true
}

start_ollama_service_with_retry() {
  local attempt=1
  local max_attempts=2

  while (( attempt <= max_attempts )); do
    if docker compose --profile ollama up -d ollama; then
      return 0
    fi

    if (( attempt == max_attempts )); then
      break
    fi

    echo "  [WARN] Ollama start failed (attempt $attempt/$max_attempts). Retrying with clean compose state..."
    docker compose --profile ollama down --remove-orphans >/dev/null 2>&1 || true
    cleanup_stale_ollama_containers
    sleep 2
    attempt=$((attempt + 1))
  done

  echo "  [FAIL] Could not start ollama service after retries."
  return 1
}

echo "==============================================="
echo "  MediSprache -- First-Run Setup"
echo "==============================================="
echo ""

provider="${LLM_PROVIDER:-}"
provider="$(normalize_provider "$provider")"

if [[ -z "$provider" ]]; then
  if [[ -t 0 ]]; then
    provider="$(prompt_provider)"
  else
    echo "[FAIL] LLM_PROVIDER must be set to 'ollama' or 'gemini' in non-interactive mode."
    exit 1
  fi
fi

if [[ "$provider" != "ollama" && "$provider" != "gemini" ]]; then
  echo "[FAIL] Unsupported LLM_PROVIDER '$provider'. Allowed values: ollama, gemini."
  exit 1
fi

delete_env_key "OLLAMA_MODEL" "$ENV_FILE"
delete_env_key "GEMINI_MODEL" "$ENV_FILE"
delete_env_key "OLLAMA_MODEL" "$AGENT_ENV_FILE"
delete_env_key "GEMINI_MODEL" "$AGENT_ENV_FILE"
unset OLLAMA_MODEL || true
unset GEMINI_MODEL || true

upsert_env_value "LLM_PROVIDER" "$provider" "$ENV_FILE"
upsert_env_value "GOOGLE_GENAI_USE_VERTEXAI" "false" "$ENV_FILE"

if [[ "$provider" == "ollama" ]]; then
  upsert_env_value "OLLAMA_API_BASE" "$DEFAULT_OLLAMA_API_BASE" "$ENV_FILE"
else
  gemini_api_key="${GOOGLE_API_KEY:-${GEMINI_API_KEY:-}}"
  if [[ -z "$gemini_api_key" ]]; then
    gemini_api_key="$(get_env_file_value "GOOGLE_API_KEY" "$ENV_FILE")"
  fi
  if [[ -z "$gemini_api_key" ]]; then
    gemini_api_key="$(get_env_file_value "GEMINI_API_KEY" "$ENV_FILE")"
  fi

  if [[ -z "$gemini_api_key" ]]; then
    if [[ -t 0 ]]; then
      read -r -s -p "Enter Gemini API key: " gemini_api_key
      echo ""
    else
      echo "[FAIL] GOOGLE_API_KEY or GEMINI_API_KEY is required for gemini provider."
      exit 1
    fi
  fi

  if [[ -z "$gemini_api_key" ]]; then
    echo "[FAIL] Gemini API key cannot be empty."
    exit 1
  fi

  upsert_env_value "GOOGLE_API_KEY" "$gemini_api_key" "$ENV_FILE"
fi

sync_agent_env_file

echo "Provider: $provider"
if [[ "$provider" == "ollama" ]]; then
  echo "Model: $FIXED_OLLAMA_MODEL"
else
  echo "Model: $FIXED_GEMINI_MODEL"
fi
echo "Gemini auth mode: GOOGLE_GENAI_USE_VERTEXAI=false"
echo "Agent env file: $AGENT_ENV_FILE"

echo ""
prepare_wsl_docker_config
echo "[1/3] Pulling base images + building custom images (parallel)..."
if [[ "$provider" == "ollama" ]]; then
  docker compose --profile ollama pull &
  PID_PULL=$!

  docker compose --profile ollama build &
  PID_BUILD=$!
else
  docker compose pull backend frontend &
  PID_PULL=$!

  docker compose build backend frontend &
  PID_BUILD=$!
fi

if wait "$PID_PULL"; then
  echo "  [OK] Image pulls complete"
else
  echo "  [FAIL] Image pull failed"
  kill "$PID_BUILD" 2>/dev/null || true
  wait "$PID_BUILD" 2>/dev/null || true
  exit 1
fi

wait "$PID_BUILD" && echo "  [OK] Builds complete" || {
  echo "  [FAIL] Build failed"
  exit 1
}

echo ""
if [[ "$provider" == "ollama" ]]; then
  echo "[2/3] Pre-downloading Ollama model ($FIXED_OLLAMA_MODEL)..."
  cleanup_stale_ollama_containers
  start_ollama_service_with_retry

  echo "  Waiting for Ollama server..."
  until docker compose --profile ollama exec ollama ollama list > /dev/null 2>&1; do
    sleep 2
  done

  echo "  Ollama server is ready. Pulling model..."
  docker compose --profile ollama exec ollama ollama pull "$FIXED_OLLAMA_MODEL"
  echo "  [OK] Model $FIXED_OLLAMA_MODEL downloaded"
else
  echo "[2/3] Skipping Ollama model download (Gemini provider selected)."
fi

echo ""
echo "[3/3] Starting services..."
if [[ "$provider" == "ollama" ]]; then
  docker compose --profile ollama up
else
  docker compose up
fi
