#!/usr/bin/env bash
# Encerra o SwiftSend com segurança e só então inicia o instalador/atualização.
# Uso: apply_update.sh <pid> <installer_path> [timeout_sec]

set -u

TARGET_PID="${1:-}"
INSTALLER="${2:-}"
TIMEOUT_SEC="${3:-10}"
LOG="${TMPDIR:-/tmp}/swiftsend-update.log"

log() {
  printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >>"$LOG" 2>/dev/null || true
}

if [[ -z "$TARGET_PID" || -z "$INSTALLER" ]]; then
  log "ERROR: usage: apply_update.sh <pid> <installer> [timeout]"
  exit 1
fi

if [[ ! -f "$INSTALLER" ]]; then
  log "ERROR: installer not found: $INSTALLER"
  exit 2
fi

log "apply_update start pid=$TARGET_PID installer=$INSTALLER timeout=$TIMEOUT_SEC"

if kill -0 "$TARGET_PID" 2>/dev/null; then
  kill -TERM "$TARGET_PID" 2>/dev/null || true
  log "SIGTERM sent"
  elapsed=0
  while kill -0 "$TARGET_PID" 2>/dev/null; do
    if (( elapsed >= TIMEOUT_SEC )); then
      log "force kill after timeout"
      kill -KILL "$TARGET_PID" 2>/dev/null || true
      sleep 0.5
      break
    fi
    sleep 0.4
    elapsed=$((elapsed + 1))
  done
else
  log "process already gone"
fi

if kill -0 "$TARGET_PID" 2>/dev/null; then
  log "ERROR: process still alive; abort installer"
  exit 3
fi

log "starting installer"
chmod +x "$INSTALLER" 2>/dev/null || true

case "$(uname -s)" in
  Darwin)
    open "$INSTALLER" || {
      log "ERROR: open failed"
      exit 4
    }
    ;;
  *)
    # AppImage / binário: inicia em background
    nohup "$INSTALLER" >/dev/null 2>&1 &
    ;;
esac

log "done"
exit 0
