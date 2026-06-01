#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# backup_db.sh — Respaldo diario de la base de datos SQLite
# Corre cada día a las 3 AM via LaunchAgent
# Guarda hasta 30 backups (30 días de historial)
# ─────────────────────────────────────────────────────────────────────────────

DB="/Users/constanza/6. Claude Constanza/rayosx/rayosx.db"
BACKUP_DIR="/Users/constanza/6. Claude Constanza/rayosx/backups"
LOG="/Users/constanza/6. Claude Constanza/rayosx/logs/backup.log"
KEEP_DAYS=30
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M')

mkdir -p "$BACKUP_DIR"

# ── Verificar que la DB existe ────────────────────────────────────────────────
if [[ ! -f "$DB" ]]; then
    echo "[$TIMESTAMP] ERROR — DB no encontrada: $DB" >> "$LOG"
    exit 1
fi

# ── Backup online usando SQLite .backup (safe con WAL mode) ──────────────────
DEST="$BACKUP_DIR/rayosx_$TIMESTAMP.db"
python3 -c "
import sqlite3, sys
src = sys.argv[1]
dst = sys.argv[2]
src_conn = sqlite3.connect(src)
dst_conn = sqlite3.connect(dst)
src_conn.backup(dst_conn)
dst_conn.close()
src_conn.close()
print('ok')
" "$DB" "$DEST" 2>>"$LOG"

if [[ $? -ne 0 ]]; then
    echo "[$TIMESTAMP] ERROR — falló el backup" >> "$LOG"
    exit 1
fi

# ── Verificar integridad del backup ──────────────────────────────────────────
INTEGRITY=$(python3 -c "
import sqlite3, sys
conn = sqlite3.connect(sys.argv[1])
r = conn.execute('PRAGMA integrity_check').fetchone()[0]
sessions = conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
conn.close()
print(f'{r}|{sessions}')
" "$DEST" 2>/dev/null)

INTEG=$(echo "$INTEGRITY" | cut -d'|' -f1)
SESSIONS=$(echo "$INTEGRITY" | cut -d'|' -f2)

if [[ "$INTEG" != "ok" ]]; then
    echo "[$TIMESTAMP] ERROR — backup corrupto: $INTEG" >> "$LOG"
    rm -f "$DEST"
    exit 1
fi

SIZE=$(du -sh "$DEST" 2>/dev/null | cut -f1)
echo "[$TIMESTAMP] OK — $DEST ($SIZE, $SESSIONS sesiones)" >> "$LOG"

# ── Eliminar backups viejos (mantener últimos 30 días) ───────────────────────
find "$BACKUP_DIR" -name "rayosx_*.db" -mtime +$KEEP_DAYS -delete
TOTAL=$(find "$BACKUP_DIR" -name "rayosx_*.db" | wc -l | tr -d ' ')
echo "[$TIMESTAMP] Backups disponibles: $TOTAL" >> "$LOG"

# ── Actualizar registro CSV ────────────────────────────────────────────────────
/opt/homebrew/bin/python3 "/Users/constanza/6. Claude Constanza/rayosx/scripts/generar_registro.py" 2>>"$LOG"
