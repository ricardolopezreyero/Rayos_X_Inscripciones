#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# worker_deploy.sh — Despliega el Worker de Cloudflare para Rayos X
#
# El Worker intercepta errores 502/503/504 del origen y muestra una página
# de mantenimiento bonita en lugar del error genérico de Cloudflare.
#
# USO: bash cloudflared/worker_deploy.sh
# NOTA: Si falla por token, hacerlo manual en:
#   https://dash.cloudflare.com → Workers & Pages → Create Worker
# ─────────────────────────────────────────────────────────────────────────────

ACCOUNT_ID="93695b987a7460c681c06ca4df901ef4"
TOKEN="TU_CLOUDFLARE_TOKEN_AQUI"
WORKER_NAME="rayosx-gateway"
SCRIPT_PATH="$(dirname "$0")/worker_maintenance.js"

echo "Desplegando worker '$WORKER_NAME'..."

RESPONSE=$(curl -s -X PUT \
  "https://api.cloudflare.com/client/v4/accounts/$ACCOUNT_ID/workers/scripts/$WORKER_NAME" \
  -H "Authorization: Bearer $TOKEN" \
  -F "metadata={\"main_module\":\"worker.js\",\"compatibility_date\":\"2025-01-01\"};type=application/json" \
  -F "worker.js=@$SCRIPT_PATH;type=application/javascript+module")

SUCCESS=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('success','false'))" 2>/dev/null)

if [[ "$SUCCESS" == "True" ]]; then
    echo "✓ Worker desplegado exitosamente"
    echo ""
    echo "Ahora agrega la ruta en Cloudflare Dashboard:"
    echo "  Workers & Pages → $WORKER_NAME → Settings → Triggers"
    echo "  Agregar ruta: rayosx.superleads.mx/*"
else
    echo "✗ Error al desplegar (posible restricción de IP en el token)"
    echo ""
    echo "Hazlo manual en 2 minutos:"
    echo "  1. dash.cloudflare.com → Workers & Pages → Create Worker"
    echo "  2. Pega el código de: cloudflared/worker_maintenance.js"
    echo "  3. Deploy → Settings → Triggers → Add route: rayosx.superleads.mx/*"
    echo ""
    echo "Respuesta API: $RESPONSE"
fi
