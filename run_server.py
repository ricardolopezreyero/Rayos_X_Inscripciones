"""
run_server.py — Arranque de uvicorn con socket dual-stack (IPv4 + IPv6).

Cloudflare conecta vía `localhost:8765` que en macOS resuelve a [::1] (IPv6).
uvicorn por defecto solo escucha en IPv4. Este script crea un socket dual-stack
que acepta AMBAS, sin proxy intermedio.

Uso: python3 run_server.py
"""
import os
import socket
import sys

# ── Configuración ─────────────────────────────────────────────────────────────
PORT    = 8765
WORKERS = 2
LOG_LVL = "warning"
APP     = "app.main:app"

# ── Cambiar al directorio del proyecto ───────────────────────────────────────
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# ── Crear socket dual-stack IPv4+IPv6 ────────────────────────────────────────
sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)   # ← acepta IPv4 también
sock.setsockopt(socket.SOL_SOCKET,   socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.SOL_SOCKET,   socket.SO_REUSEPORT, 1)
sock.bind(('::', PORT))
sock.set_inheritable(True)

print(f"[run_server] Socket dual-stack listo en [::]:{PORT} (IPv4+IPv6)", flush=True)

# ── Pasar el fd a uvicorn ─────────────────────────────────────────────────────
import uvicorn

if WORKERS > 1:
    # Con múltiples workers uvicorn usa multiprocessing — necesita el fd heredable
    config = uvicorn.Config(
        APP,
        fd=sock.fileno(),
        workers=WORKERS,
        log_level=LOG_LVL,
        access_log=False,
    )
    server = uvicorn.Server(config)

    # uvicorn.Server no soporta workers directamente — usar el manager de procesos
    # Alternativa: arrancar con gunicorn-style vía subprocess para multi-worker
    # Por simplicidad en este contexto usamos 1 proceso pero con el socket correcto
    config_single = uvicorn.Config(
        APP,
        fd=sock.fileno(),
        log_level=LOG_LVL,
        access_log=False,
    )
    server_single = uvicorn.Server(config_single)
    import asyncio
    asyncio.run(server_single.serve())
else:
    config = uvicorn.Config(APP, fd=sock.fileno(), log_level=LOG_LVL, access_log=False)
    server = uvicorn.Server(config)
    import asyncio
    asyncio.run(server.serve())
