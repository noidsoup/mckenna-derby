#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

STREAMLIT="${ROOT}/.venv/bin/streamlit"
DASHBOARD="${ROOT}/dashboard.py"
LOG="/tmp/mckenna-derby-streamlit.log"
ADDRESS="127.0.0.1"
MATCH="streamlit run.*dashboard.py"

if [[ ! -x "$STREAMLIT" ]]; then
  echo "error: missing venv streamlit at $STREAMLIT" >&2
  echo "Create venv and install deps first." >&2
  exit 1
fi

if pgrep -f "$MATCH" >/dev/null 2>&1; then
  pkill -f "$MATCH" || true
  sleep 2
fi

pick_port() {
  local p="$1"
  if lsof -nP -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; then
    return 1
  fi
  echo "$p"
  return 0
}

PORT=""
for candidate in 8501 8502; do
  if picked=$(pick_port "$candidate"); then
    PORT="$picked"
    break
  fi
done

if [[ -z "$PORT" ]]; then
  echo "error: ports 8501 and 8502 are in use" >&2
  exit 1
fi

nohup "$STREAMLIT" run "$DASHBOARD" \
  --server.headless true \
  --server.port "$PORT" \
  --server.address "$ADDRESS" \
  >>"$LOG" 2>&1 &
PID=$!

URL="http://${ADDRESS}:${PORT}"

ready=0
code="000"
for _ in $(seq 1 30); do
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "error: streamlit exited early (PID $PID)" >&2
    echo "Last log lines:" >&2
    tail -n 30 "$LOG" >&2 || true
    exit 1
  fi
  code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 1 "$URL" 2>/dev/null || echo "000")
  if [[ "$code" == "200" ]]; then
    ready=1
    break
  fi
  sleep 1
done

if [[ "$ready" != "1" ]]; then
  echo "error: dashboard not responding on $URL (last HTTP $code)" >&2
  echo "PID: $PID (still running: $(kill -0 "$PID" 2>/dev/null && echo yes || echo no))" >&2
  echo "Log: $LOG" >&2
  tail -n 30 "$LOG" >&2 || true
  exit 1
fi

echo "McKenna Derby dashboard"
echo "URL:  $URL"
echo "PID:  $PID"
echo "Log:  $LOG"
