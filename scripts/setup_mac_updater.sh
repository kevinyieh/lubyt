#!/usr/bin/env bash
# Install, manage, or uninstall the 1-minute macOS launchd updater for Capybara Clock.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUSH_SCRIPT="${SCRIPT_DIR}/push_local.sh"
ENV_DIR="${HOME}/.config/capybara-clock"
ENV_FILE="${ENV_DIR}/env"
LOG_FILE="${HOME}/Library/Logs/capybara-clock.log"
LABEL="com.capybaraclock.updater"
PLIST_PATH="${HOME}/Library/LaunchAgents/${LABEL}.plist"
UID_NUM="$(id -u)"

case "${1:-install}" in
  --uninstall|uninstall)
    launchctl bootout "gui/${UID_NUM}/${LABEL}" 2>/dev/null || launchctl unload "${PLIST_PATH}" 2>/dev/null || true
    rm -f "${PLIST_PATH}"
    echo "Uninstalled ${LABEL} (${PLIST_PATH})."
    echo "Your credentials in ${ENV_FILE} were left untouched (delete manually if desired)."
    exit 0
    ;;
  --status|status)
    echo "=== LaunchAgent Status ==="
    launchctl print "gui/${UID_NUM}/${LABEL}" 2>/dev/null | grep -E "state =|last exit code|runs =" || echo "Not loaded."
    echo ""
    echo "=== Recent Logs (${LOG_FILE}) ==="
    tail -n 15 "${LOG_FILE}" 2>/dev/null || echo "(no logs yet)"
    exit 0
    ;;
  --run-now|run)
    exec "${PUSH_SCRIPT}" --foreground
    ;;
  install|--install)
    ;;
  *)
    echo "Usage: $0 [install | --status | --run-now | --uninstall]"
    exit 1
    ;;
esac

mkdir -p "${ENV_DIR}" "${HOME}/Library/LaunchAgents" "${HOME}/Library/Logs"
chmod +x "${PUSH_SCRIPT}"

if [ ! -f "${ENV_FILE}" ]; then
  echo "Creating ${ENV_FILE} (stored locally outside Git with chmod 600)..."
  read -r -p "Tidbyt Device ID: " INPUT_DEVICE_ID
  read -r -s -p "Tidbyt API Key: " INPUT_API_KEY
  echo ""
  read -r -p "Zip Code (optional, leave blank for Brooklyn NY default): " INPUT_ZIP
  read -r -p "Timezone (optional, leave blank to auto-detect from location): " INPUT_TZ
  read -r -p "Temperature unit [F/C] (default F): " INPUT_UNIT
  INPUT_UNIT="${INPUT_UNIT:-F}"

  cat > "${ENV_FILE}" <<EOF
# Capybara Clock local updater credentials & config (chmod 600, NOT in Git)
TIDBYT_DEVICE_ID="${INPUT_DEVICE_ID}"
TIDBYT_API_KEY="${INPUT_API_KEY}"
CAPYBARA_ZIP_CODE="${INPUT_ZIP}"
CAPYBARA_TIMEZONE="${INPUT_TZ}"
CAPYBARA_TEMP_UNIT="${INPUT_UNIT}"
CAPYBARA_USE_24H="false"
CAPYBARA_BACKGROUND="true"
EOF
  chmod 600 "${ENV_FILE}"
  echo "Saved credentials to ${ENV_FILE}."
else
  echo "Using existing credentials in ${ENV_FILE}."
fi

# Write LaunchAgent plist firing at :02 past every single minute
cat > "${PLIST_PATH}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${PUSH_SCRIPT}</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Second</key>
    <integer>2</integer>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${LOG_FILE}</string>
  <key>StandardErrorPath</key>
  <string>${LOG_FILE}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
</dict>
</plist>
EOF

# Reload LaunchAgent cleanly
launchctl bootout "gui/${UID_NUM}/${LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/${UID_NUM}" "${PLIST_PATH}"

echo "Installed and started ${LABEL} (runs every minute at :02)."
echo "Running an immediate foreground push to verify..."
"${PUSH_SCRIPT}" --foreground
echo ""
echo "Done! Check status anytime with:"
echo "  ${SCRIPT_DIR}/setup_mac_updater.sh --status"
echo "Stop/uninstall anytime with:"
echo "  ${SCRIPT_DIR}/setup_mac_updater.sh --uninstall"
