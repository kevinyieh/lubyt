#!/usr/bin/env bash
# Render capybara_clock.star and push to Tidbyt locally (designed for macOS launchd).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${HOME}/.config/capybara-clock/env"
LOG_FILE="${HOME}/Library/Logs/capybara-clock.log"
LOCK_DIR="/tmp/capybara-clock-push.lock"
OUT_WEBP="/tmp/capybara_clock_local.webp"

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

if [ ! -f "${ENV_FILE}" ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] Missing ${ENV_FILE}. Run scripts/setup_mac_updater.sh first." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${ENV_FILE}"

if [ -z "${TIDBYT_DEVICE_ID:-}" ] || [ -z "${TIDBYT_API_KEY:-}" ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] TIDBYT_DEVICE_ID or TIDBYT_API_KEY is empty in ${ENV_FILE}." >&2
  exit 1
fi

PIXLET_BIN="$(command -v pixlet || true)"
if [ -z "${PIXLET_BIN}" ]; then
  echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] pixlet not found in PATH (${PATH})." >&2
  exit 1
fi

# Prevent overlapping pushes (clean up stale lock older than 90s)
if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  if [ -d "${LOCK_DIR}" ] && [ -n "$(find "${LOCK_DIR}" -maxdepth 0 -mmin +1 2>/dev/null)" ]; then
    rm -rf "${LOCK_DIR}"
    mkdir "${LOCK_DIR}" 2>/dev/null || exit 0
  else
    exit 0
  fi
fi
trap 'rm -rf "${LOCK_DIR}"' EXIT

RENDER_ARGS=()
[ -n "${CAPYBARA_LATITUDE:-}" ]    && RENDER_ARGS+=("latitude=${CAPYBARA_LATITUDE}")
[ -n "${CAPYBARA_LONGITUDE:-}" ]   && RENDER_ARGS+=("longitude=${CAPYBARA_LONGITUDE}")
[ -n "${CAPYBARA_ZIP_CODE:-}" ]    && RENDER_ARGS+=("zip_code=${CAPYBARA_ZIP_CODE}")
[ -n "${CAPYBARA_TIMEZONE:-}" ]    && RENDER_ARGS+=("timezone=${CAPYBARA_TIMEZONE}")
[ -n "${CAPYBARA_USE_24H:-}" ]     && RENDER_ARGS+=("use_24h=${CAPYBARA_USE_24H}")
[ -n "${CAPYBARA_TEMP_UNIT:-}" ]   && RENDER_ARGS+=("temp_unit=${CAPYBARA_TEMP_UNIT}")

# Allow optional CLI overrides (e.g. ./scripts/push_local.sh --foreground debug_weather=snow)
FOREGROUND="false"
for arg in "$@"; do
  if [ "${arg}" = "--foreground" ]; then
    FOREGROUND="true"
  else
    RENDER_ARGS+=("${arg}")
  fi
done

RENDER_OUT=""
for attempt in 1 2; do
  if RENDER_OUT="$("${PIXLET_BIN}" render "${REPO_DIR}/capybara_clock.star" "${RENDER_ARGS[@]}" -o "${OUT_WEBP}" 2>&1)"; then
    break
  fi
  if [ "${attempt}" -eq 2 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] pixlet render failed: ${RENDER_OUT}" >&2
    exit 1
  fi
  sleep 2
done

PUSH_ARGS=(
  --api-token "${TIDBYT_API_KEY}"
  --installation-id "capybaraclock"
)
if [ "${FOREGROUND}" != "true" ] && [ "${CAPYBARA_BACKGROUND:-true}" = "true" ]; then
  PUSH_ARGS+=(--background)
fi

"${PIXLET_BIN}" push "${PUSH_ARGS[@]}" "${TIDBYT_DEVICE_ID}" "${OUT_WEBP}"

SUMMARY="$(echo "${RENDER_OUT}" | tr '\n' ' ' | sed 's/  */ /g')"
echo "$(date '+%Y-%m-%d %H:%M:%S') [OK] ${SUMMARY}"

# Keep log file trimmed to the most recent 500 lines
if [ -f "${LOG_FILE}" ] && [ "$(wc -l < "${LOG_FILE}")" -gt 600 ]; then
  tail -n 500 "${LOG_FILE}" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "${LOG_FILE}"
fi
