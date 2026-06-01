#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Rayos X Watchdog v3 — corre cada 5 min via LaunchAgent
# Verifica y repara: uvicorn + cloudflared
# uvicorn escucha en IPv6 (::) → check via ::1:8765
# SIN costo de IA — bash+python puro en la Mac.
# ─────────────────────────────────────────────────────────────────────────────

LOG="/Users/constanza/6. Claude Constanza/rayosx/logs/watchdog.log"
MAX_LOG_LINES=3000
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
PYTHON=/opt/homebrew/bin/python3

# ── Función de check HTTP via IPv6 ───────────────────────────────────────────
http_check() {
    $PYTHON - <<'PYEOF' 2>/dev/null
import http.client
try:
    c = http.client.HTTPConnection("::1", 8765, timeout=8, source_address=("::1", 0))
    c.request("GET", "/healthz")
    r = c.getresponse()
    print(r.status)
except Exception:
    print(0)
PYEOF
}

# ── Rotar log si está muy grande ─────────────────────────────────────────────
if [[ -f "$LOG" ]] && (( $(wc -l < "$LOG") > MAX_LOG_LINES )); then
    tail -n 500 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi

# ── 1. Asegurar que uvicorn corre ────────────────────────────────────────────
UV=$(ps aux | grep "uvicorn app.main:app" | grep -v grep | wc -l | tr -d ' ')
if [[ "$UV" -eq 0 ]]; then
    echo "[$TIMESTAMP] WARN uvicorn no corre — reiniciando ..." >> "$LOG"
    pkill -9 -f "uvicorn app.main:app" 2>/dev/null
    sleep 2
    launchctl kickstart -k "gui/$(id -u)/mx.superleads.rayosx-app" 2>>"$LOG"
    sleep 6
fi

# ── 2. Asegurar que cloudflared corre ────────────────────────────────────────
CF=$(ps aux | grep "cloudflared.*config.yml" | grep -v grep | wc -l | tr -d ' ')
if [[ "$CF" -eq 0 ]]; then
    echo "[$TIMESTAMP] WARN cloudflared no corre — reiniciando ..." >> "$LOG"
    launchctl kickstart -k "gui/$(id -u)/mx.superleads.rayosx-tunnel" 2>>"$LOG"
    sleep 4
fi

# ── 3. Check HTTP ─────────────────────────────────────────────────────────────
response=$(http_check)

if [[ "$response" == "200" ]]; then
    echo "[$TIMESTAMP] OK" >> "$LOG"
    exit 0
fi

# ── 4. Repair de emergencia ───────────────────────────────────────────────────
echo "[$TIMESTAMP] FAIL HTTP=$response — repair completo ..." >> "$LOG"

pkill -9 -f "uvicorn app.main:app"    2>/dev/null
pkill -9 -f "cloudflared.*config.yml" 2>/dev/null
sleep 4

launchctl kickstart -k "gui/$(id -u)/mx.superleads.rayosx-app"    2>>"$LOG"
sleep 7
launchctl kickstart -k "gui/$(id -u)/mx.superleads.rayosx-tunnel" 2>>"$LOG"
sleep 5

response2=$(http_check)
if [[ "$response2" == "200" ]]; then
    echo "[$TIMESTAMP] RECOVERED ✓" >> "$LOG"
else
    echo "[$TIMESTAMP] ERROR sigue caído (HTTP $response2) — requiere atención manual" >> "$LOG"
fi
