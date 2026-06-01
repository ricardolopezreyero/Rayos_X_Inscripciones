#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# wake_recovery.sh — Se ejecuta cuando la Mac se despierta del sueño
# o cuando la red reconecta. Verifica que cloudflared y uvicorn estén vivos.
# ─────────────────────────────────────────────────────────────────────────────

LOG="/Users/constanza/6. Claude Constanza/rayosx/logs/wake.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
PYTHON=/opt/homebrew/bin/python3

echo "[$TIMESTAMP] Mac despertó / red reconectó — verificando servicios ..." >> "$LOG"

# Dar tiempo a que la red estabilice
sleep 8

# ── Verificar y reparar uvicorn ───────────────────────────────────────────────
UV=$(ps aux | grep "uvicorn app.main:app" | grep -v grep | wc -l | tr -d ' ')
if [[ "$UV" -eq 0 ]]; then
    echo "[$TIMESTAMP] uvicorn caído tras wake — reiniciando ..." >> "$LOG"
    launchctl kickstart -k "gui/$(id -u)/mx.superleads.rayosx-app" 2>>"$LOG"
    sleep 7
fi

# ── Reconectar cloudflared (siempre lo reiniciamos en wake) ─────────────────
# El tunnel puede tener conexiones rancias tras el sleep
echo "[$TIMESTAMP] Reconectando cloudflared ..." >> "$LOG"
launchctl kickstart -k "gui/$(id -u)/mx.superleads.rayosx-tunnel" 2>>"$LOG"
sleep 5

# ── Verificar que responde ────────────────────────────────────────────────────
STATUS=$($PYTHON - <<'PYEOF' 2>/dev/null
import http.client
try:
    c = http.client.HTTPConnection("::1", 8765, timeout=8, source_address=("::1", 0))
    c.request("GET", "/healthz")
    r = c.getresponse()
    print(r.status)
except Exception:
    print(0)
PYEOF
)

if [[ "$STATUS" == "200" ]]; then
    echo "[$TIMESTAMP] OK — servicios listos tras wake ✓" >> "$LOG"
else
    echo "[$TIMESTAMP] WARN — no responde tras wake (HTTP $STATUS), watchdog lo atenderá en 5 min" >> "$LOG"
fi
