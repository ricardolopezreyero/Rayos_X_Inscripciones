#!/bin/bash
PDFS="/Users/constanza/6. Claude Constanza/rayosx/static/pdfs"
LOG="/Users/constanza/6. Claude Constanza/rayosx/logs/cleanup.log"
echo "[$(date '+%Y-%m-%d %H:%M')] Cleaning PDFs older than 60 days..." >> "$LOG"
find "$PDFS" -name "*.pdf" -mtime +60 -print -delete >> "$LOG" 2>&1
COUNT=$(ls "$PDFS"/*.pdf 2>/dev/null | wc -l | tr -d ' ')
echo "[$(date '+%Y-%m-%d %H:%M')] Done. PDFs remaining: $COUNT" >> "$LOG"
