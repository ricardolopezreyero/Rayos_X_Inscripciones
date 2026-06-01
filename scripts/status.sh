#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# status.sh — Diagnóstico rápido de Rayos X en la Mac
# Corre: bash scripts/status.sh
# ─────────────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'; BOLD='\033[1m'
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }

echo -e "\n${BOLD}═══ Rayos X — Estado del sistema $(date '+%H:%M:%S') ═══${NC}\n"

# ── Uvicorn ──────────────────────────────────────────────────────────────────
echo -e "${BOLD}1. uvicorn (app Python)${NC}"
UV=$(ps aux | grep "uvicorn app.main:app" | grep -v grep | wc -l | tr -d ' ')
if [[ "$UV" -gt 0 ]]; then
    PID=$(ps aux | grep "uvicorn app.main:app" | grep -v grep | awk 'NR==1{print $2}')
    ok "Corriendo — $UV procesos (PID maestro: $PID)"
else
    fail "NO CORRE"
fi
LISTEN=$(lsof -i :8765 2>/dev/null | grep LISTEN | wc -l | tr -d ' ')
[[ "$LISTEN" -gt 0 ]] && ok "Escuchando en puerto 8765 ($LISTEN sockets)" || fail "Puerto 8765 no escucha"

# ── IPv6 Proxy ───────────────────────────────────────────────────────────────
# ── Cloudflared ──────────────────────────────────────────────────────────────
echo -e "\n${BOLD}2. Cloudflare Tunnel${NC}"
CF=$(ps aux | grep "cloudflared tunnel" | grep -v grep | wc -l | tr -d ' ')
[[ "$CF" -gt 0 ]] && ok "Tunnel activo ($CF procesos)" || fail "Tunnel NO corre"
# Revisar log de conexión reciente
LAST=$(grep "Registered tunnel" "/Users/constanza/6. Claude Constanza/rayosx/logs/cloudflared.log" 2>/dev/null | tail -1)
[[ -n "$LAST" ]] && ok "Última conexión: $(echo $LAST | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]+Z')" || warn "Sin info de conexión"

# ── LaunchAgents ─────────────────────────────────────────────────────────────
echo -e "\n${BOLD}3. LaunchAgents (auto-restart)${NC}"
for label in mx.superleads.rayosx-app mx.superleads.rayosx-tunnel mx.superleads.rayosx-watchdog; do
    STATUS=$(launchctl list | grep "$label" | awk '{print $1, $2}')
    PID=$(echo $STATUS | awk '{print $1}')
    EXIT=$(echo $STATUS | awk '{print $2}')
    if [[ "$PID" != "-" && "$PID" != "" ]]; then
        ok "$label (PID $PID)"
    elif [[ "$label" == "mx.superleads.rayosx-watchdog" ]]; then
        ok "$label (inactivo entre runs — normal)"
    else
        fail "$label NO está cargado"
    fi
done

# ── Conectividad HTTP local ───────────────────────────────────────────────────
echo -e "\n${BOLD}4. Conectividad HTTP (IPv6)${NC}"
R=$(python3 -c "
import http.client, sys
try:
    c=http.client.HTTPConnection('::1',8765,timeout=5,source_address=('::1',0))
    c.request('GET','/healthz'); r=c.getresponse(); print(r.status)
except: print(0)
" 2>/dev/null)
[[ "$R" == "200" ]] && ok "[::1]:8765/healthz → 200 OK" || fail "[::1]:8765 no responde (HTTP $R)"

# ── Watchdog log ─────────────────────────────────────────────────────────────
echo -e "\n${BOLD}6. Últimos eventos del watchdog${NC}"
tail -3 "/Users/constanza/6. Claude Constanza/rayosx/logs/watchdog.log" 2>/dev/null | while read line; do
    [[ "$line" == *"OK"* ]] && ok "$line" || warn "$line"
done

echo ""
