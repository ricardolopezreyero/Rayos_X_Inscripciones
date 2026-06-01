"""
IPv6 → IPv4 TCP proxy para Cloudflare tunnel.

Cloudflare conecta a localhost:8765 que en macOS resuelve a [::1]:8765 (IPv6).
uvicorn escucha en 127.0.0.1:8765 (IPv4).
Este proxy escucha en [::1]:8765 y reenvía todo a 127.0.0.1:8765.
"""
import asyncio
import logging
import signal
import socket
import sys

LISTEN_HOST = "::1"
LISTEN_PORT = 8765
TARGET_HOST = "127.0.0.1"
TARGET_PORT = 8765

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [ipv6-proxy] %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        while chunk := await reader.read(65536):
            writer.write(chunk)
            await writer.drain()
    except (asyncio.IncompleteReadError, ConnectionResetError):
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def handle(client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
    try:
        target_reader, target_writer = await asyncio.open_connection(TARGET_HOST, TARGET_PORT)
    except OSError as e:
        log.error("No se pudo conectar a uvicorn: %s", e)
        client_writer.close()
        return

    await asyncio.gather(
        _pipe(client_reader, target_writer),
        _pipe(target_reader, client_writer),
    )


async def main():
    server = await asyncio.start_server(
        handle,
        host=LISTEN_HOST,
        port=LISTEN_PORT,
        reuse_address=True,
        family=socket.AF_INET6,
    )
    addr = server.sockets[0].getsockname()
    log.warning("IPv6 proxy escuchando en [%s]:%s → %s:%s", addr[0], addr[1], TARGET_HOST, TARGET_PORT)

    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)
    loop.add_signal_handler(signal.SIGINT,  stop.set_result, None)

    async with server:
        await stop


if __name__ == "__main__":
    asyncio.run(main())
