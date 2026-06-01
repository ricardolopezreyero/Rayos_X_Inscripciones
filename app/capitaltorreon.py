"""CapitalTorreon — BTC Bot Dashboard.

Monta en /CapitalTorreon. Lee los archivos que escribe el bot Java:
  - prices_BTC.csv
  - event_log.txt
  - satoshi_log.csv
  - settings.properties

Configura CAPITALXRP_DATA_DIR para apuntar al directorio del bot.
"""
from __future__ import annotations

import csv
import io
import math
import os
import re
import sqlite3
import time
import urllib.request
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Response
from fastapi.responses import HTMLResponse, JSONResponse

# ── Ruta a los archivos del bot Java ─────────────────────────────────────────
_DEFAULT_DATA_DIR = "/Users/constanza/Downloads/INFO COMPLETA CAPITALXRP"
DATA_DIR = os.environ.get("CAPITALXRP_DATA_DIR", _DEFAULT_DATA_DIR)

PRICES_FILE   = os.path.join(DATA_DIR, "prices_BTC.csv")
EVENTS_FILE   = os.path.join(DATA_DIR, "event_log.txt")
SATOSHI_FILE  = os.path.join(DATA_DIR, "satoshi_log.csv")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.properties")

DB_FILE = os.path.join(DATA_DIR, "capitalxrp.db")

router = APIRouter(prefix="/CapitalTorreon", tags=["CapitalTorreon"])

# ── Cache simple para no releer archivos grandes en cada request ───────────
_cache: dict = {}
_CACHE_TTL = 15  # segundos


def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and time.time() - entry["ts"] < _CACHE_TTL:
        return entry["val"]
    return None


def _cache_set(key: str, val):
    _cache[key] = {"val": val, "ts": time.time()}
    return val


# ── Parsers ───────────────────────────────────────────────────────────────────

_MEXICO_TZ = timezone(timedelta(hours=-6))  # CST (UTC-6)

_MONTH_ES = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
    "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9,
    "octubre": 10, "noviembre": 11, "diciembre": 12,
}

_RX_DATE = re.compile(
    r"(\d{1,2})\s+de\s+(\w+)\s+(\d{4})\s+(\d{2}):(\d{2})",
    re.IGNORECASE,
)
_RX_DATE2 = re.compile(r"(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})")


def _parse_price_ts(raw: str) -> Optional[datetime]:
    raw = raw.replace("CST", "").replace("CDT", "").strip()
    m = _RX_DATE.search(raw)
    if m:
        d, month_s, y, hh, mm = m.groups()
        mo = _MONTH_ES.get(month_s.lower())
        if mo:
            try:
                return datetime(int(y), mo, int(d), int(hh), int(mm),
                                tzinfo=_MEXICO_TZ)
            except ValueError:
                pass
    m2 = _RX_DATE2.search(raw)
    if m2:
        y, mo, d, hh, mm, ss = m2.groups()
        return datetime(int(y), int(mo), int(d), int(hh), int(mm), int(ss),
                        tzinfo=_MEXICO_TZ)
    return None


def _parse_event_ts(raw: str) -> Optional[datetime]:
    raw = raw.replace("CST", "").replace("CDT", "").replace(" z", "").strip()
    m = _RX_DATE2.search(raw)
    if m:
        y, mo, d, hh, mm, ss = m.groups()
        return datetime(int(y), int(mo), int(d), int(hh), int(mm), int(ss),
                        tzinfo=_MEXICO_TZ)
    return None


def _read_prices(since_days: int = 400) -> list[dict]:
    cached = _cache_get(f"prices_{since_days}")
    if cached is not None:
        return cached

    if not os.path.exists(PRICES_FILE):
        return _cache_set(f"prices_{since_days}", [])

    cutoff = datetime.now(_MEXICO_TZ) - timedelta(days=since_days)
    out = []
    with open(PRICES_FILE, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",", 1)
            if len(parts) < 2:
                continue
            ts = _parse_price_ts(parts[0])
            if ts is None or ts < cutoff:
                continue
            try:
                price = float(parts[1].replace("USD", "").replace("$", "").strip())
                out.append({"t": ts.isoformat(), "p": price})
            except ValueError:
                pass

    out.sort(key=lambda x: x["t"])
    return _cache_set(f"prices_{since_days}", out)


_EVENT_TYPE_MAP = {
    "STOPLOSS": "stopLoss", "STOP": "stopLoss",
    "SAFESELL": "safeSell", "TP": "safeSell", "TAKEPROFIT": "safeSell",
    "SAFEBUY": "safeBuy", "REBUY": "safeBuy", "RECOMPRA": "safeBuy",
    "MAXIMO": "sell", "MÁXIMO": "sell", "HIGH": "sell", "VENTA": "sell",
    "MINIMO": "buy", "MÍNIMO": "buy", "LOW": "buy", "COMPRA": "buy",
    "DEPOSITO": "deposit", "DEPÓSITO": "deposit",
}

_RX_MONEY = re.compile(r"\$([\d,]+(?:\.[\d]+)?)")  # acepta $73,635.77 y $73635.77


def _map_event(raw: str) -> Optional[str]:
    n = raw.upper().replace(" ", "")
    for k, v in _EVENT_TYPE_MAP.items():
        if k in n:
            return v
    return None


def _read_events(since_days: int = 400) -> list[dict]:
    cached = _cache_get(f"events_{since_days}")
    if cached is not None:
        return cached

    if not os.path.exists(EVENTS_FILE):
        return _cache_set(f"events_{since_days}", [])

    cutoff = datetime.now(_MEXICO_TZ) - timedelta(days=since_days)
    out = []
    rx_line = re.compile(r"^\[(.*?)\]\s*EVENTO:\s*(.*)$")

    with open(EVENTS_FILE, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if "EVENTO:" not in line:
                continue
            if "modificado desde la web" in line:
                continue
            m = rx_line.match(line)
            if not m:
                continue
            ts = _parse_event_ts(m.group(1))
            if ts is None or ts < cutoff:
                continue
            rest = m.group(2).strip()
            raw_name = rest.split(" - ")[0].strip()
            etype = _map_event(raw_name)
            if etype is None:
                continue

            # Depósitos: extraer monto del campo "cantidad=$X"
            if etype == "deposit":
                m_dep = re.search(r"cantidad=\$?([\d.]+)", rest, re.IGNORECASE)
                if not m_dep:
                    continue
                amount = float(m_dep.group(1))
                out.append({
                    "t": ts.isoformat(),
                    "p": amount,          # monto depositado
                    "type": "deposit",
                    "name": raw_name,
                    "deposit_amount": amount,
                })
                continue

            # Precio: buscar en todo el detalle (con o sin $, con o sin comas)
            prices = _RX_MONEY.findall(rest)
            # Fallback: buscar precio sin signo $ (formato antiguo: precio=73635.18)
            if not prices:
                m_p = re.search(r'precio[=:\s]*([\d,]+(?:\.[\d]+)?)', rest, re.IGNORECASE)
                if m_p:
                    prices = [m_p.group(1)]
            if not prices:
                continue
            price = float(prices[0].replace(",", ""))

            # Extraer z-score y RSI del detalle completo del evento
            z_val = rsi_val = macd_val = None
            m_z   = re.search(r'\bz[=:\s]*(-?[\d.]+)', rest, re.IGNORECASE)
            m_rsi = re.search(r'\brsi[=:\s]*([\d.]+)', rest, re.IGNORECASE)
            m_mac = re.search(r'macd[=:\s]*([↑↓→\w+-]+)', rest)
            if m_z:   z_val   = round(float(m_z.group(1)), 3)
            if m_rsi: rsi_val = round(float(m_rsi.group(1)), 1)
            if m_mac: macd_val = m_mac.group(1)

            out.append({
                "t":    ts.isoformat(),
                "p":    price,
                "type": etype,
                "name": raw_name,
                "z":    z_val,
                "rsi":  rsi_val,
                "macd": macd_val,
            })

    out.sort(key=lambda x: x["t"])

    # ── Deduplicar: operaciones del mismo "grupo" (buy/safeBuy o sell/safeSell)
    # que ocurren en el mismo minuto son la misma operación registrada dos veces.
    # Fusionamos: z/rsi del primero + precio del más reciente.
    BUY_TYPES  = {"buy", "safeBuy"}
    SELL_TYPES = {"sell", "safeSell", "stopLoss"}

    def same_group(t1: str, t2: str) -> bool:
        return (t1 in BUY_TYPES and t2 in BUY_TYPES) or \
               (t1 in SELL_TYPES and t2 in SELL_TYPES)

    deduped: list[dict] = []
    for ev in out:
        minute = ev["t"][:16]  # YYYY-MM-DDTHH:MM
        # Buscar evento del mismo grupo en el mismo minuto
        prev = next(
            (e for e in deduped
             if e["t"][:16] == minute and same_group(e["type"], ev["type"])),
            None
        )
        if prev:
            # Fusionar: z/rsi del que los tenga, precio del más reciente (suele ser el formateado)
            if ev.get("z") is not None and prev.get("z") is None:
                prev["z"]    = ev["z"]
                prev["rsi"]  = ev["rsi"]
                prev["macd"] = ev["macd"]
            # Actualizar precio si el nuevo tiene mayor precisión (más decimales significativos)
            if ev["p"] and abs(ev["p"] - prev["p"]) < 1.0:
                prev["p"] = ev["p"]
        else:
            deduped.append(ev)

    return _cache_set(f"events_{since_days}", deduped)


def _read_settings() -> dict:
    cached = _cache_get("settings")
    if cached is not None:
        return cached

    if not os.path.exists(SETTINGS_FILE):
        return _cache_set("settings", {})

    props = {}
    with open(SETTINGS_FILE, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, _, v = line.partition("=")
                props[k.strip()] = v.strip()
    return _cache_set("settings", props)


def _parse_real_trades() -> list[dict]:
    """Parse BUY-SUCCESS / SELL-SUCCESS blocks from event_log to get real FDUSD flows."""
    cached = _cache_get("real_trades")
    if cached is not None:
        return cached

    if not os.path.exists(EVENTS_FILE):
        return _cache_set("real_trades", [])

    trades: list[dict] = []
    rx_ts    = re.compile(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*[A-Z]*\]')
    rx_acc_b = re.compile(r'\[BUY-SUCCESS\]\[(\w+)\]')
    rx_acc_s = re.compile(r'\[SELL-SUCCESS\]\[(\w+)\]')
    rx_xrp_b = re.compile(r'Comprado:\s*([\d.]+)\s*BTC')
    rx_xrp_s = re.compile(r'Vendido:\s*([\d.]+)\s*BTC')
    rx_price_b = re.compile(r'Precio unitario real de compra:\s*\$([\d.]+)')
    rx_price_s = re.compile(r'Precio unitario de venta:\s*\$([\d.]+)')
    rx_fdusd_b = re.compile(r'Total gastado:\s*\$([\d.]+)')
    rx_fdusd_s = re.compile(r'Total recibido:\s*\$([\d.]+)')

    cur: dict = {}

    def flush(trade: dict):
        if trade.get('type') and trade.get('t') and trade.get('fdusd'):
            trades.append(dict(trade))

    with open(EVENTS_FILE, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip()
            if not line:
                continue
            if 'BUY-SUCCESS' in line and 'Resumen de compra' in line:
                flush(cur); cur = {}
                m_ts = rx_ts.match(line); m_acc = rx_acc_b.search(line)
                if m_ts and m_acc:
                    ts = _parse_event_ts(m_ts.group(1))
                    cur = {'type': 'buy', 'account': m_acc.group(1), 't': ts}
            elif 'SELL-SUCCESS' in line and 'Resumen de venta' in line:
                flush(cur); cur = {}
                m_ts = rx_ts.match(line); m_acc = rx_acc_s.search(line)
                if m_ts and m_acc:
                    ts = _parse_event_ts(m_ts.group(1))
                    cur = {'type': 'sell', 'account': m_acc.group(1), 't': ts}
            elif cur:
                if cur['type'] == 'buy':
                    m = rx_xrp_b.search(line)
                    if m: cur['xrp'] = float(m.group(1))
                    m = rx_price_b.search(line)
                    if m: cur['price'] = float(m.group(1))
                    m = rx_fdusd_b.search(line)
                    if m:
                        cur['fdusd'] = float(m.group(1))
                        flush(cur); cur = {}
                else:
                    m = rx_xrp_s.search(line)
                    if m: cur['xrp'] = float(m.group(1))
                    m = rx_price_s.search(line)
                    if m: cur['price'] = float(m.group(1))
                    m = rx_fdusd_s.search(line)
                    if m:
                        cur['fdusd'] = float(m.group(1))
                        flush(cur); cur = {}

    flush(cur)
    trades.sort(key=lambda x: x['t'].isoformat() if x.get('t') else '')
    return _cache_set("real_trades", trades)


def _get_total_deposited() -> float:
    """
    Suma todos los depósitos externos detectados en event_log.txt.
    Excluidos del cálculo de ROI — son entradas de capital, no ganancias de trading.
    """
    events = _read_events(since_days=400)
    deposits = [e for e in events if e.get("type") == "deposit"]
    return sum(e.get("deposit_amount", e.get("p", 0)) for e in deposits)


def _parse_cycles_from_events() -> list[dict]:
    """
    Extrae ciclos completos (compra→venta) directamente del event_log.txt.
    Más fiable que _parse_real_trades() que buscaba formato BUY-SUCCESS/SELL-SUCCESS
    que nunca se escribe en el log de eventos.
    """
    events = _read_events(since_days=400)
    cycles = []
    last_buy: Optional[dict] = None

    for ev in sorted(events, key=lambda x: x["t"]):
        if ev["type"] in ("buy", "safeBuy"):
            last_buy = ev
        elif ev["type"] in ("sell", "safeSell", "stopLoss") and last_buy:
            buy_p  = last_buy["p"]
            sell_p = ev["p"]
            if buy_p > 0:
                roi_pct = (sell_p / buy_p - 1) * 100
                cycles.append({
                    "t_buy":   last_buy["t"],
                    "t_sell":  ev["t"],
                    "buy_p":   buy_p,
                    "sell_p":  sell_p,
                    "roi_pct": round(roi_pct, 4),
                    "won":     sell_p > buy_p,
                    "type_sell": ev["type"],
                })
            last_buy = None
    return cycles


def _compute_growth_metrics(current_price: Optional[float] = None) -> dict:
    """
    ROI real de trading usando ciclos completos del event_log.
    Crecimiento compuesto = producto de (1 + roi_i) para cada ciclo.
    """
    cached = _cache_get("growth_metrics")
    if cached is not None:
        return cached

    cycles = _parse_cycles_from_events()
    now    = datetime.now(_MEXICO_TZ)

    windows = {
        "total": None,
        "24h":   now - timedelta(hours=24),
        "7d":    now - timedelta(days=7),
        "30d":   now - timedelta(days=30),
    }

    result: dict = {}
    for label, cutoff in windows.items():
        wc = [c for c in cycles if cutoff is None or c["t_sell"] >= cutoff.isoformat()]
        n_cycles = len(wc)
        n_wins   = sum(1 for c in wc if c["won"])

        if n_cycles > 0:
            # Crecimiento compuesto real
            compound = 1.0
            for c in wc:
                compound *= (1 + c["roi_pct"] / 100)
            growth_pct = (compound - 1) * 100
            avg_roi    = sum(c["roi_pct"] for c in wc) / n_cycles
        else:
            growth_pct = avg_roi = 0.0

        result[label] = {
            "growth_pct": round(growth_pct, 4),
            "avg_roi":    round(avg_roi, 4),
            "cycles":     n_cycles,
            "wins":       n_wins,
            "win_rate":   round(n_wins / n_cycles * 100, 1) if n_cycles > 0 else 0.0,
        }

    # Equity curve: ROI compuesto acumulado por día usando los ciclos reales
    daily_roi: dict[str, float] = {}
    for c in cycles:
        day = c["t_sell"][:10]  # YYYY-MM-DD
        daily_roi[day] = daily_roi.get(day, 0.0) + c["roi_pct"]

    cum_compound = 1.0
    equity_curve: list[dict] = []
    for day in sorted(daily_roi.keys()):
        cum_compound *= (1 + daily_roi[day] / 100)
        equity_curve.append({"t": day, "equity": round((cum_compound - 1) * 100, 4)})

    result["equity_curve"]    = equity_curve
    result["xrp_held"]        = 0.0
    result["unrealized_usd"]  = 0.0
    return _cache_set("growth_metrics", result)


def _read_satoshi_balances() -> dict:
    cached = _cache_get("satoshi")
    if cached is not None:
        return cached

    if not os.path.exists(SATOSHI_FILE):
        return _cache_set("satoshi", {})

    result: dict = {}
    try:
        with open(SATOSHI_FILE, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if not headers:
                return _cache_set("satoshi", {})
            accounts = headers[1:]
            last_row = None
            first_row = None
            for row in reader:
                if len(row) < 2:
                    continue
                if first_row is None:
                    first_row = row
                last_row = row

            if last_row:
                for i, acc in enumerate(accounts):
                    try:
                        result[acc] = {
                            "current": float(last_row[i + 1]) if i + 1 < len(last_row) else 0.0,
                            "ts": last_row[0],
                        }
                    except (ValueError, IndexError):
                        pass

            if first_row and last_row and first_row[0] != last_row[0]:
                for i, acc in enumerate(accounts):
                    try:
                        start = float(first_row[i + 1]) if i + 1 < len(first_row) else 0.0
                        cur = result.get(acc, {}).get("current", 0.0)
                        if start > 0:
                            result[acc]["growth_total_pct"] = (cur / start - 1) * 100
                            result[acc]["start"] = start
                    except (ValueError, IndexError):
                        pass
    except Exception:
        pass

    return _cache_set("satoshi", result)


def _fetch_live_price() -> Optional[float]:
    cached = _cache_get("live_price")
    if cached is not None:
        return cached

    try:
        url = "https://api.mexc.com/api/v3/ticker/price?symbol=BTCUSDT"
        req = urllib.request.Request(url, headers={"User-Agent": "CapitalTorreon/1.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            import json
            data = json.loads(r.read().decode())
            price = float(data["price"])
            _cache_set("live_price", price)
            _cache["live_price"]["ts"] = time.time() - (_CACHE_TTL - 8)  # expire in 8s
            return price
    except Exception:
        return None


def _infer_bot_state(events: list[dict]) -> str:
    """Infer HOLD_TRADE_XRP or HOLD_TRADE_USD from last trade event."""
    for ev in reversed(events):
        t = ev.get("type", "")
        if t in ("sell", "safeSell", "stopLoss"):
            return "HOLD_TRADE_USD"
        if t in ("buy", "safeBuy"):
            return "HOLD_TRADE_XRP"
    return "HOLD_TRADE_XRP"


def _compute_stats(events: list[dict], prices: list[dict]) -> dict:
    """Métricas de rendimiento basadas en ciclos completos del event_log."""
    cycles = _parse_cycles_from_events()
    buys   = [e for e in events if e["type"] in ("buy", "safeBuy")]
    sells  = [e for e in events if e["type"] in ("sell", "safeSell", "stopLoss")]

    wins       = sum(1 for c in cycles if c["won"])
    losses     = sum(1 for c in cycles if not c["won"])
    total      = len(cycles)
    win_rate   = round(wins / total * 100, 1) if total > 0 else 0.0
    avg_profit = round(sum(c["roi_pct"] for c in cycles) / total, 4) if total > 0 else 0.0

    return {
        "total_trades":   total,
        "wins":           wins,
        "losses":         losses,
        "win_rate":       win_rate,
        "avg_profit_pct": avg_profit,
        "total_buys":     len(buys),
        "total_sells":    len(sells),
    }


# ── Rutas API ─────────────────────────────────────────────────────────────────

@router.get("/api/prices")
async def api_prices(range: str = "7d"):
    days_map = {"1d": 1, "7d": 7, "1m": 30, "3m": 90, "1y": 365, "all": 400}
    days = days_map.get(range, 7)
    pts = _read_prices(since_days=days)
    # Downsample para rangos largos
    if len(pts) > 2000:
        step = len(pts) // 2000 + 1
        pts = pts[::step]
    return JSONResponse({"t": [p["t"] for p in pts], "p": [p["p"] for p in pts]})


@router.get("/api/events")
async def api_events(range: str = "7d"):
    days_map = {"1d": 1, "7d": 7, "1m": 30, "3m": 90, "1y": 365, "all": 400}
    days = days_map.get(range, 7)
    evs = _read_events(since_days=days)
    return JSONResponse(evs)


@router.get("/api/live")
async def api_live():
    price = _fetch_live_price()
    events_all = _read_events(since_days=400)
    state = _infer_bot_state(events_all)
    settings = _read_settings()
    sat = _read_satoshi_balances()

    total_xrp = sum(v.get("current", 0) for v in sat.values())
    total_growth = {}
    for acc, v in sat.items():
        s = v.get("start", 0)
        c = v.get("current", 0)
        total_growth[acc] = round((c / s - 1) * 100, 4) if s > 0 else 0

    # Z-score y RSI: leer directo del SQLite (bot los escribe cada tick).
    # Fallback: cálculo aproximado solo si la DB no tiene datos recientes.
    z_score = None
    rsi_approx = None
    bot_state_db = None

    conn = _db_connect()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT z_score, rsi, bot_state
                FROM algo_ticks
                ORDER BY ts DESC LIMIT 1
            """)
            row = cur.fetchone()
            if row and row[0] is not None:
                z_score    = round(float(row[0]), 3)
                rsi_approx = round(float(row[1]), 1) if row[1] is not None else None
                bot_state_db = row[2]
            conn.close()
        except Exception:
            try: conn.close()
            except Exception: pass

    # Si la DB no tenía datos, caer al cálculo aproximado pero con ventana amplia
    if z_score is None:
        prices_1d = _read_prices(since_days=1)
        if prices_1d and len(prices_1d) >= 60:
            recents = [p["p"] for p in prices_1d[-120:]]
            # EMA-10 rápida con ventana amplia para evitar z extremos
            mean_fast = sum(recents[-10:]) / 10
            window = recents[-60:]  # std sobre 60 períodos, no 30
            mean_w = sum(window) / len(window)
            variance = sum((x - mean_w) ** 2 for x in window) / len(window)
            std = math.sqrt(variance) if variance > 0 else 1.0
            current = price or recents[-1]
            raw_z = (current - mean_fast) / std if std > 0 else 0
            z_score = round(max(-5.0, min(5.0, raw_z)), 3)  # clamped ±5σ

            if len(recents) >= 15:
                gains = [max(recents[i] - recents[i-1], 0) for i in range(1, len(recents))]
                losses_l = [max(recents[i-1] - recents[i], 0) for i in range(1, len(recents))]
                avg_gain = sum(gains[-14:]) / 14
                avg_loss = sum(losses_l[-14:]) / 14
                if avg_loss > 0:
                    rsi_approx = round(100 - 100 / (1 + avg_gain / avg_loss), 1)
                else:
                    rsi_approx = 99.0  # evitar 100.0 exacto que suena a bug

    # Preferir estado del DB si disponible
    if bot_state_db:
        state = bot_state_db

    return JSONResponse({
        "price": price,
        "state": state,
        "z_score": z_score,
        "rsi": rsi_approx,
        "total_xrp": round(total_xrp, 6),
        "balances": sat,
        "growth": total_growth,
        "settings": {
            k: settings.get(k) for k in [
                "TRADE_PCT", "Z_BUY", "Z_SELL", "EMA_FAST_MINUTES",
                "EMA_SLOW_MINUTES", "STD_WINDOW_MINUTES", "COOLDOWN_MINUTES",
                "GOAL_ASSET", "Z_SELL_TURBO", "EXTRA_SELL_PCT",
            ] if k in settings
        },
    })


@router.get("/api/stats")
async def api_stats():
    events = _read_events(since_days=400)
    prices = _read_prices(since_days=30)
    stats = _compute_stats(events, prices)
    return JSONResponse(stats)


@router.get("/api/growth")
async def api_growth():
    price = _fetch_live_price()
    metrics = _compute_growth_metrics(current_price=price)
    return JSONResponse(metrics)


# ── Notificaciones en vivo ────────────────────────────────────────────────────

_NOTIF_MAP = {
    "COMPRA":            {"emoji": "🟢", "label": "COMPRA EJECUTADA",       "theme": "green"},
    "VENTA":             {"emoji": "🔴", "label": "VENTA EJECUTADA",         "theme": "orange"},
    "PEAK-VENTA":        {"emoji": "🎯", "label": "PEAK SELL — Tope capturado", "theme": "yellow"},
    "FORZADO":           {"emoji": "🔵", "label": "Recompra Forzada",        "theme": "blue"},
    "FORZADO-FAIL":      {"emoji": "⚠️", "label": "Orden Fallida",           "theme": "red"},
    "STOP LOSS":         {"emoji": "🛑", "label": "Stop Loss ejecutado",     "theme": "red"},
    "INICIALIZACIÓN-V5": {"emoji": "🚀", "label": "Bot Iniciado",            "theme": "purple"},
    "INICIALIZACIÓN-V6": {"emoji": "🚀", "label": "Bot Iniciado v6",         "theme": "purple"},
    "INICIALIZACIÓN-V7": {"emoji": "🚀", "label": "Bot Iniciado v7",         "theme": "purple"},
}

_RX_NOTIF_LINE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})[^\]]*\]\s*EVENTO:\s*(.+?)\s+-\s+(.+)$")
_RX_PRECIO = re.compile(r"precio[=:\s]*\$?([\d,]+(?:\.[\d]+)?)", re.IGNORECASE)
_RX_PCT    = re.compile(r"pct[=:\s]*([\d.]+)", re.IGNORECASE)
_RX_Z      = re.compile(r"\bz[=:\s]*(-?[\d.]+)", re.IGNORECASE)


def _read_notifications(since_iso: str = "") -> list[dict]:
    if not os.path.exists(EVENTS_FILE):
        return []

    since_dt: Optional[datetime] = None
    if since_iso:
        try:
            since_dt = datetime.fromisoformat(since_iso)
            if since_dt.tzinfo is None:
                since_dt = since_dt.replace(tzinfo=_MEXICO_TZ)
        except ValueError:
            pass

    # Read last 300 lines efficiently (avoid loading huge log file)
    try:
        with open(EVENTS_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        lines = lines[-300:]
    except OSError:
        return []

    out: list[dict] = []
    for line in lines:
        line = line.strip()
        if "EVENTO:" not in line:
            continue
        if "modificado desde la web" in line:
            continue
        m = _RX_NOTIF_LINE.match(line)
        if not m:
            continue
        ts = _parse_event_ts(m.group(1))
        if ts is None:
            continue
        if since_dt and ts <= since_dt:
            continue

        raw_type = m.group(2).strip().upper()
        detail   = m.group(3).strip()

        # Normalise type key (case-insensitive prefix match)
        notif_key = next((k for k in _NOTIF_MAP if raw_type.startswith(k.upper())), None)
        if notif_key is None:
            continue

        cfg = _NOTIF_MAP[notif_key]

        # Extract price if present
        mp = _RX_PRECIO.search(detail)
        price_val = float(mp.group(1).replace(",", "")) if mp else None

        # Extract % and z for subtitle
        mp2 = _RX_PCT.search(detail)
        mz  = _RX_Z.search(detail)
        subtitle_parts = []
        if price_val:
            subtitle_parts.append(f"${price_val:.4f}")
        if mp2:
            subtitle_parts.append(f"{float(mp2.group(1)):.1f}% BTC")
        if mz and notif_key in ("VENTA", "COMPRA", "PEAK-VENTA"):
            subtitle_parts.append(f"z={float(mz.group(1)):.3f}")

        out.append({
            "t":        ts.isoformat(),
            "type":     notif_key,
            "emoji":    cfg["emoji"],
            "label":    cfg["label"],
            "theme":    cfg["theme"],
            "subtitle": " · ".join(subtitle_parts) if subtitle_parts else detail[:60],
            "price":    price_val,
        })

    out.sort(key=lambda x: x["t"])
    return out


@router.get("/api/notifications")
async def api_notifications(since: str = ""):
    items = _read_notifications(since_iso=since)
    return JSONResponse(items)


# ── Endpoints de base de datos SQLite ────────────────────────────────────────

def _db_connect():
    """Conexión de solo lectura al SQLite del bot."""
    if not os.path.exists(DB_FILE):
        return None
    conn = sqlite3.connect(f"file:{DB_FILE}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/api/db/summary")
async def api_db_summary():
    cached = _cache_get("db_summary")
    if cached is not None:
        return JSONResponse(cached)
    conn = _db_connect()
    if conn is None:
        return JSONResponse({"error": "DB no disponible aún (el bot la crea al arrancar)"})
    try:
        cur = conn.cursor()
        out: dict = {}

        # Ciclos totales
        cur.execute("SELECT COUNT(*), COALESCE(SUM(won),0), COALESCE(AVG(roi_pct),0), COALESCE(AVG(duration_min),0) FROM trade_cycles")
        r = cur.fetchone()
        out["cycles_total"]      = r[0]
        out["wins_total"]        = r[1]
        out["avg_roi_pct"]       = round(r[2], 3)
        out["avg_duration_min"]  = round(r[3], 1)
        out["win_rate_pct"]      = round(r[1] / r[0] * 100, 1) if r[0] > 0 else 0

        # Últimas 24h
        cur.execute("SELECT COUNT(*), COALESCE(SUM(won),0), COALESCE(AVG(roi_pct),0) FROM trade_cycles WHERE buy_ts >= datetime('now','-1 day')")
        r = cur.fetchone()
        out["cycles_24h"] = r[0]
        out["wins_24h"]   = r[1]
        out["avg_roi_24h"]= round(r[2], 3)

        # Últimos 7d
        cur.execute("SELECT COUNT(*), COALESCE(SUM(won),0), COALESCE(AVG(roi_pct),0) FROM trade_cycles WHERE buy_ts >= datetime('now','-7 days')")
        r = cur.fetchone()
        out["cycles_7d"] = r[0]
        out["wins_7d"]   = r[1]
        out["avg_roi_7d"]= round(r[2], 3)

        # Conteos de tablas
        cur.execute("SELECT COUNT(*) FROM price_ticks")
        out["price_ticks"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM algo_ticks")
        out["algo_ticks"] = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM orders WHERE status='FILLED'")
        out["orders_filled"] = cur.fetchone()[0]

        # Última orden
        cur.execute("SELECT side, price_avg, qty_coin, qty_quote, ts, trigger FROM orders WHERE status='FILLED' ORDER BY ts DESC LIMIT 1")
        r = cur.fetchone()
        if r:
            out["last_order"] = {"side": r[0], "price": round(r[1],4), "qty_coin": round(r[2],4),
                                  "qty_quote": round(r[3],2), "ts": r[4], "trigger": r[5]}

        # Mejor y peor ciclo
        cur.execute("SELECT buy_ts, sell_ts, roi_pct, trigger FROM trade_cycles ORDER BY roi_pct DESC LIMIT 1")
        r = cur.fetchone()
        if r: out["best_cycle"] = {"buy_ts": r[0], "sell_ts": r[1], "roi_pct": round(r[2],3), "trigger": r[3]}
        cur.execute("SELECT buy_ts, sell_ts, roi_pct, trigger FROM trade_cycles ORDER BY roi_pct ASC LIMIT 1")
        r = cur.fetchone()
        if r: out["worst_cycle"] = {"buy_ts": r[0], "sell_ts": r[1], "roi_pct": round(r[2],3), "trigger": r[3]}

        # Triggers más frecuentes en ventas
        cur.execute("SELECT trigger, COUNT(*) as n FROM trade_cycles WHERE trigger IS NOT NULL GROUP BY trigger ORDER BY n DESC")
        out["triggers"] = [{"trigger": r[0], "count": r[1]} for r in cur.fetchall()]

        conn.close()
        return JSONResponse(_cache_set("db_summary", out))
    except Exception as e:
        conn.close()
        return JSONResponse({"error": str(e)})


@router.get("/api/db/cycles")
async def api_db_cycles(limit: int = 50):
    cached = _cache_get(f"db_cycles_{limit}")
    if cached is not None:
        return JSONResponse(cached)
    conn = _db_connect()
    if conn is None:
        return JSONResponse([])
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT buy_ts, sell_ts, buy_price, sell_price, roi_pct,
                   duration_min, trigger, won, coin_delta
            FROM trade_cycles ORDER BY buy_ts DESC LIMIT ?""", (limit,))
        rows = [{"buy_ts": r[0], "sell_ts": r[1], "buy_price": round(r[2],4),
                 "sell_price": round(r[3],4), "roi_pct": round(r[4],3),
                 "duration_min": r[5], "trigger": r[6], "won": r[7],
                 "coin_delta": round(r[8],6) if r[8] else 0}
                for r in cur.fetchall()]
        conn.close()
        return JSONResponse(_cache_set(f"db_cycles_{limit}", rows))
    except Exception as e:
        conn.close()
        return JSONResponse({"error": str(e)})


@router.get("/api/db/indicators")
async def api_db_indicators(hours: int = 6):
    """Últimas N horas de indicadores para análisis."""
    conn = _db_connect()
    if conn is None:
        return JSONResponse([])
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT ts, price, z_score, rsi, macd_hist, trend_score, bot_state, action, std_pct
            FROM algo_ticks
            WHERE ts >= datetime('now', ? || ' hours')
            ORDER BY ts ASC""", (f"-{hours}",))
        rows = [{"ts": r[0], "price": r[1], "z": r[2], "rsi": r[3],
                 "macd_hist": r[4], "trend": r[5], "state": r[6],
                 "action": r[7], "std_pct": r[8]}
                for r in cur.fetchall()]
        conn.close()
        return JSONResponse(rows)
    except Exception as e:
        conn.close()
        return JSONResponse({"error": str(e)})


@router.get("/api/balance")
async def api_balance():
    """Balance en vivo de la cuenta MEXC (USDT + BTC)."""
    import hmac as _hmac, hashlib as _hl, json as _json
    cached = _cache_get("mexc_balance")
    if cached is not None:
        return JSONResponse(cached)
    settings = _read_settings()
    api_key    = settings.get("mexc_apiKeyMain", "")
    api_secret = settings.get("mexc_apiSecretMain", "")
    if not api_key or not api_secret:
        return JSONResponse({"error": "Sin credenciales"})
    try:
        ts  = int(time.time() * 1000)
        qs  = f"timestamp={ts}"
        sig = _hmac.new(api_secret.encode(), qs.encode(), _hl.sha256).hexdigest()
        url = f"https://api.mexc.com/api/v3/account?{qs}&signature={sig}"
        req = urllib.request.Request(url, headers={
            "Accept": "application/json", "X-MEXC-APIKEY": api_key
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            data = _json.loads(r.read())
        usdt = btc = 0.0
        for b in data.get("balances", []):
            if b["asset"] == "USDT":
                usdt = float(b["free"]) + float(b.get("locked", 0))
            elif b["asset"] == "BTC":
                btc  = float(b["free"]) + float(b.get("locked", 0))
        price = _fetch_live_price() or 0.0
        total = usdt + btc * price
        out = {"usdt": round(usdt, 2), "btc": round(btc, 8),
               "btc_price": round(price, 2), "total_usdt": round(total, 2)}
        _cache["mexc_balance"] = {"val": out, "ts": time.time() - (_CACHE_TTL - 30)}
        return JSONResponse(out)
    except Exception as e:
        return JSONResponse({"error": str(e)})


DAILY_SNAPSHOT_FILE = os.path.join(DATA_DIR, "daily_value.csv")

@router.get("/api/portfolio")
async def api_portfolio():
    """
    Snapshots diarios de cartera (3:33 PM CDMX).
    Lee daily_value.csv: fecha,btc_portfolio,precio_btc,usdt_total
    Añade el punto de HOY con el valor en vivo (aunque no sean las 3:33).
    Devuelve los últimos 30 días.
    """
    cached = _cache_get("portfolio_daily")
    if cached is not None:
        return JSONResponse(cached)

    points = []
    # Leer snapshots históricos del CSV
    if os.path.exists(DAILY_SNAPSHOT_FILE):
        try:
            with open(DAILY_SNAPSHOT_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    parts = line.split(",")
                    if len(parts) < 4: continue
                    try:
                        fecha, btc_p, precio, usdt_t = parts[0], float(parts[1]), float(parts[2]), float(parts[3])
                        points.append({"t": fecha, "btc_portfolio": btc_p,
                                       "precio_btc": precio, "usdt_total": usdt_t,
                                       "is_live": False})
                    except ValueError:
                        continue
        except Exception:
            pass

    # Añadir punto de hoy con valor en vivo (siempre al final)
    try:
        import hmac as _hmac, hashlib as _hl, json as _json, time as _time
        settings = _read_settings()
        ak = settings.get("mexc_apiKeyMain",""); sk = settings.get("mexc_apiSecretMain","")
        if ak and sk:
            ts = int(_time.time() * 1000)
            qs = f"timestamp={ts}"
            sig = _hmac.new(sk.encode(), qs.encode(), _hl.sha256).hexdigest()
            req = urllib.request.Request(
                f"https://api.mexc.com/api/v3/account?{qs}&signature={sig}",
                headers={"Accept":"application/json","X-MEXC-APIKEY":ak})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = _json.loads(r.read())
            free_btc = free_usdt = 0.0
            for b in data.get("balances", []):
                if b["asset"] == "BTC":  free_btc  = float(b["free"])
                if b["asset"] == "USDT": free_usdt = float(b["free"])
            # Precio actual
            req2 = urllib.request.Request(
                "https://api.mexc.com/api/v3/ticker/price?symbol=BTCUSDT",
                headers={"Accept":"application/json"})
            with urllib.request.urlopen(req2, timeout=5) as r:
                price_now = float(_json.loads(r.read())["price"])
            btc_portfolio = free_btc + (free_usdt / price_now if price_now > 0 else 0)
            usdt_total    = free_btc * price_now + free_usdt
            today = datetime.now(_MEXICO_TZ).strftime("%Y-%m-%d")
            # Solo añadir si hoy no tiene snapshot histórico
            if not points or points[-1]["t"] != today:
                points.append({"t": today, "btc_portfolio": btc_portfolio,
                                "precio_btc": price_now, "usdt_total": usdt_total,
                                "is_live": True})
            else:
                # Actualizar el punto de hoy con el valor en vivo
                points[-1].update({"btc_portfolio": btc_portfolio,
                                   "precio_btc": price_now, "usdt_total": usdt_total,
                                   "is_live": True})
    except Exception:
        pass

    # Últimos 30 días
    points = sorted(points, key=lambda x: x["t"])[-30:]
    # Cache corta: 5 min (se actualiza cuando llega a las 3:33)
    _cache["portfolio_daily"] = {"val": points, "ts": time.time() - (_CACHE_TTL - 300)}
    return JSONResponse(points)


# ── Página principal ─────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTMLResponse(_DASHBOARD_HTML)


# ── HTML del Dashboard ────────────────────────────────────────────────────────

_DASHBOARD_HTML = """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>CapitalTorreon · BTC/USDT</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
  <style>
    /* ═══════════════════════════════════════════════
       CapitalTorreon — Neural Finance Design System
       ═══════════════════════════════════════════════ */
    :root {
      --bg:         #050a14;
      --surface:    rgba(8,16,34,0.92);
      --surface-hi: rgba(12,22,48,0.95);
      --border:     rgba(255,255,255,0.055);
      --border-hi:  rgba(255,255,255,0.14);
      --text:       #eef2ff;
      --text-2:     #94a3b8;
      --muted:      #475569;
      --orange:     #ff5c1a;
      --green:      #00d97e;
      --red:        #ff3355;
      --blue:       #3b7cff;
      --yellow:     #ffc107;
      --purple:     #9b5de5;
      --cyan:       #00cfff;
      --gold:       #f59e0b;
      --gap: 14px;
      --r:   18px;
      --r-lg: 24px;
    }
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg);
      background-image:
        radial-gradient(ellipse 120% 55% at 50% -8%,  rgba(59,124,255,0.10) 0%, transparent 60%),
        radial-gradient(ellipse 55%  45% at 92%  88%,  rgba(255,92,26,0.07)  0%, transparent 55%),
        radial-gradient(ellipse 45%  35% at 8%   82%,  rgba(155,93,229,0.05) 0%, transparent 50%);
      color: var(--text);
      min-height: 100vh;
      padding: 14px 16px;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }

    .shell { width: 100%; }

    /* ════════  HEADER  ════════ */
    .header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 13px 22px;
      background: var(--surface-hi);
      border: 1px solid var(--border-hi);
      border-radius: var(--r-lg);
      margin-bottom: var(--gap);
      backdrop-filter: blur(28px);
      -webkit-backdrop-filter: blur(28px);
      position: relative; overflow: hidden;
    }
    .header::before {
      content: '';
      position: absolute; top: 0; left: 0; right: 0; height: 1px;
      background: linear-gradient(90deg,
        transparent 0%, rgba(59,124,255,.7) 30%,
        rgba(255,92,26,.7) 70%, transparent 100%);
    }
    .brand { display: flex; align-items: center; gap: 13px; }
    .brand-name { font-size: 20px; font-weight: 800; letter-spacing: -0.8px; line-height: 1.1; }
    .brand-name span { color: var(--orange); }
    .brand-sub { font-size: 10px; color: var(--muted); letter-spacing: .5px; margin-top: 2px; }
    .header-right { display: flex; align-items: center; gap: 14px; }
    .live-badge {
      display: flex; align-items: center; gap: 7px;
      font-size: 11px; color: var(--green); font-weight: 700; letter-spacing: .5px;
      background: rgba(0,217,126,.08); border: 1px solid rgba(0,217,126,.2);
      padding: 5px 12px; border-radius: 999px;
    }
    .live-dot {
      width: 7px; height: 7px; border-radius: 50%; background: var(--green);
      animation: livePulse 2s ease-in-out infinite;
    }
    @keyframes livePulse {
      0%,100% { box-shadow: 0 0 0 0 rgba(0,217,126,.6); }
      60%      { box-shadow: 0 0 0 5px rgba(0,217,126,0); }
    }
    .last-update { font-size: 10px; color: var(--muted); letter-spacing: .3px; }

    /* ════════  KPI GRID  ════════ */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      gap: var(--gap); margin-bottom: var(--gap);
    }
    .growth-section {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: var(--gap); margin-bottom: var(--gap);
    }
    .kpi-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--r);
      padding: 17px 18px 15px;
      position: relative; overflow: hidden; cursor: default;
      transition: transform .18s ease, border-color .2s, box-shadow .2s;
    }
    .kpi-card:hover { transform: translateY(-3px); border-color: var(--border-hi); }
    .kpi-card::before {
      content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    }
    /* Watermark icon */
    .kpi-card::after {
      content: attr(data-icon);
      position: absolute; right: 14px; bottom: 8px;
      font-size: 40px; line-height: 1;
      opacity: 0.04; pointer-events: none; user-select: none;
      transition: opacity .2s;
    }
    .kpi-card:hover::after { opacity: 0.07; }

    .kpi-card.orange::before { background: linear-gradient(90deg, var(--orange), rgba(255,92,26,.3)); box-shadow: 0 0 18px rgba(255,92,26,.35); }
    .kpi-card.green::before  { background: linear-gradient(90deg, var(--green),  rgba(0,217,126,.3)); box-shadow: 0 0 18px rgba(0,217,126,.35); }
    .kpi-card.blue::before   { background: linear-gradient(90deg, var(--blue),   rgba(59,124,255,.3)); box-shadow: 0 0 18px rgba(59,124,255,.35); }
    .kpi-card.yellow::before { background: linear-gradient(90deg, var(--yellow), rgba(255,193,7,.3)); box-shadow: 0 0 18px rgba(255,193,7,.35); }
    .kpi-card.red::before    { background: linear-gradient(90deg, var(--red),    rgba(255,51,85,.3)); box-shadow: 0 0 18px rgba(255,51,85,.35); }
    .kpi-card.purple::before { background: linear-gradient(90deg, var(--purple), rgba(155,93,229,.3)); box-shadow: 0 0 18px rgba(155,93,229,.35); }
    .kpi-card.cyan::before   { background: linear-gradient(90deg, var(--cyan),   rgba(0,207,255,.3)); box-shadow: 0 0 18px rgba(0,207,255,.35); }

    .kpi-card.orange:hover { box-shadow: 0 14px 44px rgba(255,92,26,.13),  0 0 0 1px rgba(255,92,26,.18); }
    .kpi-card.green:hover  { box-shadow: 0 14px 44px rgba(0,217,126,.13),  0 0 0 1px rgba(0,217,126,.18); }
    .kpi-card.blue:hover   { box-shadow: 0 14px 44px rgba(59,124,255,.13), 0 0 0 1px rgba(59,124,255,.18); }
    .kpi-card.yellow:hover { box-shadow: 0 14px 44px rgba(255,193,7,.13),  0 0 0 1px rgba(255,193,7,.18); }
    .kpi-card.red:hover    { box-shadow: 0 14px 44px rgba(255,51,85,.13),  0 0 0 1px rgba(255,51,85,.18); }
    .kpi-card.purple:hover { box-shadow: 0 14px 44px rgba(155,93,229,.13), 0 0 0 1px rgba(155,93,229,.18); }
    .kpi-card.cyan:hover   { box-shadow: 0 14px 44px rgba(0,207,255,.13),  0 0 0 1px rgba(0,207,255,.18); }

    .kpi-label {
      font-size: 9px; font-weight: 700; letter-spacing: 1.1px;
      color: var(--muted); text-transform: uppercase; margin-bottom: 10px;
    }
    .kpi-value {
      font-size: 26px; font-weight: 800; letter-spacing: -1.2px;
      line-height: 1; font-variant-numeric: tabular-nums;
    }
    .kpi-sub { font-size: 10px; color: var(--muted); margin-top: 7px; line-height: 1.3; }

    .state-badge {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 5px 12px; border-radius: 999px;
      font-size: 12px; font-weight: 700; letter-spacing: .5px;
    }
    .state-xrp { background: rgba(0,217,126,.1); color: var(--green); border: 1px solid rgba(0,217,126,.25); }
    .state-usd { background: rgba(255,92,26,.1); color: var(--orange); border: 1px solid rgba(255,92,26,.25); }
    .growth-up   { color: var(--green); }
    .growth-down { color: var(--red); }

    /* ════════  CARD  ════════ */
    .main-cols  { display: flex; flex-direction: column; gap: var(--gap); margin-bottom: var(--gap); }
    .two-cols   { display: grid; grid-template-columns: 1fr 1fr; gap: var(--gap); margin-bottom: var(--gap); }
    .three-cols { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: var(--gap); margin-bottom: var(--gap); }

    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--r);
      padding: 20px 22px;
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
      transition: border-color .2s;
    }
    .card:hover { border-color: var(--border-hi); }

    .card-title {
      font-size: 10px; font-weight: 700; letter-spacing: 1px;
      color: var(--muted); text-transform: uppercase;
      margin-bottom: 16px;
      display: flex; align-items: center; gap: 8px;
    }
    /* Colored left bar accent */
    .card-title::before {
      content: '';
      display: inline-block; width: 3px; height: 13px;
      border-radius: 2px; flex-shrink: 0;
      background: var(--border-hi);
    }
    .card.c-orange .card-title::before { background: var(--orange); box-shadow: 0 0 8px var(--orange); }
    .card.c-green  .card-title::before { background: var(--green);  box-shadow: 0 0 8px var(--green); }
    .card.c-blue   .card-title::before { background: var(--blue);   box-shadow: 0 0 8px var(--blue); }
    .card.c-purple .card-title::before { background: var(--purple); box-shadow: 0 0 8px var(--purple); }
    .card.c-cyan   .card-title::before { background: var(--cyan);   box-shadow: 0 0 8px var(--cyan); }
    .card.c-yellow .card-title::before { background: var(--yellow); box-shadow: 0 0 8px var(--yellow); }
    .card.c-red    .card-title::before { background: var(--red);    box-shadow: 0 0 8px var(--red); }

    /* ════════  RANGE BUTTONS  ════════ */
    .range-row { display: flex; gap: 6px; margin-bottom: 14px; flex-wrap: wrap; align-items: center; }
    .rb {
      padding: 5px 13px; border-radius: 999px;
      border: 1px solid var(--border);
      background: transparent; color: var(--muted);
      cursor: pointer; font-size: 11px; font-weight: 600;
      letter-spacing: .3px; font-family: inherit;
      transition: all .15s;
    }
    .rb:hover  { border-color: rgba(255,92,26,.5); color: var(--orange); background: rgba(255,92,26,.05); }
    .rb.active { border-color: var(--orange); color: var(--orange); background: rgba(255,92,26,.1); box-shadow: 0 0 18px rgba(255,92,26,.16); }

    /* ════════  LIVE BUTTON  ════════ */
    .rb-live {
      display: flex; align-items: center; gap: 6px;
      padding: 5px 13px; border-radius: 999px;
      border: 1px solid rgba(0,217,126,.4);
      background: rgba(0,217,126,.08); color: var(--green);
      cursor: pointer; font-size: 11px; font-weight: 700;
      letter-spacing: .3px; font-family: inherit;
      transition: all .15s;
    }
    .rb-live:hover { background: rgba(0,217,126,.15); box-shadow: 0 0 18px rgba(0,217,126,.2); }
    .rb-live.active { background: rgba(0,217,126,.18); border-color: var(--green); box-shadow: 0 0 22px rgba(0,217,126,.3); }
    .rb-live .live-dot {
      width: 7px; height: 7px; border-radius: 50%; background: var(--green);
      animation: livePulse 2s ease-in-out infinite;
    }
    .rb-live.active .live-dot { animation: livePulse 1s ease-in-out infinite; }

    /* ════════  LIVE COUNTDOWN BAR  ════════ */
    #live-countdown-wrap {
      display: none; margin-bottom: 6px; padding: 0 2px;
    }
    #live-countdown-wrap.visible { display: flex; align-items: center; gap: 10px; }
    #live-countdown-bar-bg {
      flex: 1; height: 3px; border-radius: 99px;
      background: rgba(0,217,126,.12);
      overflow: hidden;
    }
    #live-countdown-bar {
      height: 100%; border-radius: 99px;
      background: linear-gradient(90deg, var(--green), rgba(0,217,126,.5));
      transition: width 1s linear;
      box-shadow: 0 0 6px rgba(0,217,126,.5);
    }
    #live-countdown-text {
      font-size: 10px; color: var(--green); font-weight: 700;
      letter-spacing: .5px; min-width: 36px; text-align: right;
      font-variant-numeric: tabular-nums;
    }
    /* ════════  LIVE STATS BAR  ════════ */
    .live-stats-row {
      display: flex; align-items: center; gap: 0;
      padding: 8px 14px;
      background: rgba(0,217,126,0.04);
      border: 1px solid rgba(0,217,126,0.12);
      border-radius: 12px; margin-bottom: 8px;
      flex-wrap: wrap; gap: 0;
    }
    .live-stat {
      display: flex; flex-direction: column; align-items: center;
      padding: 0 18px; min-width: 80px;
    }
    .ls-label {
      font-size: 8px; font-weight: 700; letter-spacing: 1px;
      color: var(--muted); text-transform: uppercase; margin-bottom: 3px;
    }
    .ls-val {
      font-size: 14px; font-weight: 800; color: var(--text);
      font-variant-numeric: tabular-nums; letter-spacing: -.5px;
    }
    .ls-high { color: #4ade80; }
    .ls-low  { color: #f87171; }
    .ls-up   { color: #4ade80; }
    .ls-down { color: #f87171; }
    .live-stat-sep {
      width: 1px; height: 28px; background: rgba(255,255,255,0.06); flex-shrink: 0;
    }
    /* Leyenda de símbolos — separada a la derecha */
    .live-legend {
      display: flex; align-items: center; gap: 14px;
      margin-left: auto; padding-left: 18px;
      border-left: 1px solid rgba(255,255,255,0.06);
    }
    .legend-item {
      display: flex; align-items: center; gap: 5px;
      font-size: 10px; font-weight: 600; color: var(--muted);
      letter-spacing: .3px; white-space: nowrap;
    }
    .legend-buy  { color: #4ade80; }
    .legend-sell { color: #ff5c1a; }
    .legend-stop { color: #ff3355; }

    @media (max-width: 768px) {
      .live-stats-row { gap: 8px; }
      .live-stat { padding: 0 10px; min-width: 60px; }
      .live-legend { margin-left: 0; border-left: none; padding-left: 0; border-top: 1px solid rgba(255,255,255,.06); padding-top: 8px; width: 100%; justify-content: center; }
    }

    /* ════════  Z-SCORE RULER  ════════ */
    .z-ruler-wrap { padding: 6px 0 2px; }
    .z-ruler-title {
      font-size: 9px; font-weight: 700; color: var(--muted);
      margin-bottom: 12px; text-align: center;
      letter-spacing: .14em; text-transform: uppercase;
    }
    .z-ruler-track {
      position: relative; height: 38px; border-radius: 19px; overflow: visible;
      background: linear-gradient(90deg,
        rgba(0,217,126,.6)   0%,
        rgba(0,217,126,.15)  25%,
        rgba(25,40,70,.3)    40%,
        rgba(25,40,70,.3)    60%,
        rgba(255,92,26,.15)  75%,
        rgba(255,92,26,.6)  100%
      );
      border: 1px solid var(--border-hi);
      box-shadow: inset 0 1px 0 rgba(255,255,255,.07), inset 0 -1px 0 rgba(0,0,0,.25);
    }
    .z-ruler-zone-label {
      position: absolute; top: 50%; transform: translateY(-50%);
      font-size: 8px; font-weight: 800;
      letter-spacing: .13em; pointer-events: none; text-transform: uppercase;
    }
    .z-ruler-zone-buy  { left: 12px;  color: rgba(0,217,126,.9); text-shadow: 0 0 14px rgba(0,217,126,.6); }
    .z-ruler-zone-sell { right: 12px; color: rgba(255,92,26,.9);  text-shadow: 0 0 14px rgba(255,92,26,.6); }
    .z-ruler-zone-hold { left: 50%; transform: translate(-50%,-50%); color: rgba(100,120,160,.45); }
    .z-ruler-needle {
      position: absolute; top: -9px; width: 4px; height: 56px;
      background: linear-gradient(180deg, rgba(255,255,255,0) 0%, #fff 15%, #fff 85%, rgba(255,255,255,0) 100%);
      border-radius: 3px;
      box-shadow: 0 0 8px rgba(255,255,255,.85), 0 0 22px rgba(255,255,255,.45), 0 0 45px rgba(255,255,255,.18);
      transform: translateX(-50%);
      transition: left .75s cubic-bezier(.34,1.56,.64,1);
      pointer-events: none;
    }
    .z-ruler-needle::after {
      content: attr(data-z);
      position: absolute; top: -28px; left: 50%; transform: translateX(-50%);
      background: var(--surface-hi); border: 1px solid var(--border-hi);
      color: #fff; font-size: 12px; font-weight: 800;
      padding: 3px 10px; border-radius: 8px; white-space: nowrap;
      box-shadow: 0 6px 20px rgba(0,0,0,.55); letter-spacing: -.3px;
    }
    .z-ruler-ticks { display: flex; justify-content: space-between; margin-top: 8px; padding: 0 6px; }
    .z-ruler-tick {
      font-size: 9px; color: var(--muted); text-align: center;
      min-width: 28px; font-weight: 500; font-variant-numeric: tabular-nums;
    }
    .z-ruler-tick.threshold-buy  { color: var(--green); font-weight: 800; }
    .z-ruler-tick.threshold-sell { color: var(--orange); font-weight: 800; }
    .z-ruler-tick.zero           { color: rgba(148,163,184,.45); }

    .z-status-pill {
      padding: 5px 14px; border-radius: 999px;
      font-size: 10px; font-weight: 800; letter-spacing: .08em;
      text-transform: uppercase; white-space: nowrap;
    }
    .z-status-pill.buy-zone  { background: rgba(0,217,126,.1);  color: var(--green);  border: 1px solid rgba(0,217,126,.25); box-shadow: 0 0 22px rgba(0,217,126,.12); }
    .z-status-pill.sell-zone { background: rgba(255,92,26,.1);  color: var(--orange); border: 1px solid rgba(255,92,26,.25); box-shadow: 0 0 22px rgba(255,92,26,.12); }
    .z-status-pill.hold-zone { background: rgba(35,50,80,.35);  color: var(--muted);  border: 1px solid var(--border); }
    .z-dist-row { font-size: 11px; color: var(--muted); line-height: 1.4; }
    .z-dist-val { font-weight: 800; }

    /* ════════  SIGNAL BOXES  ════════ */
    .right-col { display: flex; flex-direction: column; gap: var(--gap); }
    .signal-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .signal-box {
      background: rgba(4,10,22,.75);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px 10px 12px;
      text-align: center;
      transition: border-color .15s, background .15s;
    }
    .signal-box:hover { background: rgba(8,18,36,.9); border-color: var(--border-hi); }
    .signal-icon { font-size: 16px; margin-bottom: 5px; line-height: 1; }
    .signal-name { font-size: 8px; font-weight: 700; color: var(--muted); letter-spacing: .9px; text-transform: uppercase; }
    .signal-val  { font-size: 20px; font-weight: 800; margin-top: 5px; letter-spacing: -.8px; font-variant-numeric: tabular-nums; }
    .up   { color: var(--green); }
    .down { color: var(--red); }
    .flat { color: var(--yellow); }

    /* ════════  TABLES  ════════ */
    table { width: 100%; border-collapse: collapse; }
    th {
      color: var(--muted); font-weight: 700;
      font-size: 9px; letter-spacing: .7px; text-transform: uppercase;
      text-align: left; padding: 0 10px 10px;
      border-bottom: 1px solid var(--border);
    }
    td { padding: 10px 10px; font-size: 13px; border-bottom: 1px solid rgba(255,255,255,.032); }
    tr:last-child td { border-bottom: none; }
    tbody tr:hover td { background: rgba(255,255,255,.018); }
    .td-right { text-align: right; }
    .trade-row-buy  td:first-child { border-left: 2px solid var(--green);  padding-left: 8px; }
    .trade-row-sell td:first-child { border-left: 2px solid var(--orange); padding-left: 8px; }
    .trade-row-stop td:first-child { border-left: 2px solid var(--red);    padding-left: 8px; }

    /* ════════  SETTINGS  ════════ */
    .settings-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }
    .setting-item {
      display: flex; justify-content: space-between; align-items: center;
      padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,.032); gap: 8px;
    }
    .setting-item:last-child, .setting-item:nth-last-child(2) { border-bottom: none; }
    .setting-key { color: var(--muted); font-size: 11px; font-family: ui-monospace, 'SF Mono', monospace; }
    .setting-val { font-weight: 700; color: var(--cyan); font-size: 11px; font-family: ui-monospace, 'SF Mono', monospace; text-align: right; }

    /* ════════  ALGORITHM STEPS  ════════ */
    .algo-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .algo-step {
      display: flex; gap: 12px; align-items: flex-start;
      padding: 14px;
      background: rgba(4,10,22,.55);
      border: 1px solid var(--border);
      border-radius: 14px;
      transition: border-color .15s;
    }
    .algo-step:hover { border-color: var(--border-hi); }
    .algo-num {
      width: 26px; height: 26px; border-radius: 50%;
      background: rgba(255,92,26,.1); color: var(--orange);
      font-size: 11px; font-weight: 800;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0; border: 1px solid rgba(255,92,26,.2);
    }
    .algo-text { font-size: 12px; line-height: 1.55; color: #7080a0; }
    .algo-text strong { color: #c0cce8; font-weight: 600; }

    /* ════════  SPINNER  ════════ */
    .spinner {
      display: inline-block; width: 14px; height: 14px;
      border: 2px solid rgba(255,255,255,.07);
      border-top-color: var(--orange);
      border-radius: 50%;
      animation: spin .8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* ════════  TOASTS  ════════ */
    #toast-container {
      position: fixed; top: 18px; right: 18px;
      display: flex; flex-direction: column; gap: 8px;
      z-index: 9999; pointer-events: none;
    }
    .toast {
      min-width: 300px; max-width: 400px;
      background: rgba(6,12,26,.97);
      border-radius: 16px; padding: 13px 15px;
      display: flex; align-items: flex-start; gap: 12px;
      border: 1px solid var(--border); border-left: 3px solid;
      box-shadow: 0 24px 64px rgba(0,0,0,.75);
      pointer-events: auto; backdrop-filter: blur(24px);
      animation: toastIn .32s cubic-bezier(.22,1,.36,1), toastOut .3s ease 2.7s forwards;
    }
    @keyframes toastIn  { from { opacity:0; transform:translateX(70px) scale(.93); } to { opacity:1; transform:none; } }
    @keyframes toastOut { from { opacity:1; transform:none; } to { opacity:0; transform:translateX(70px) scale(.93); } }
    .toast.green  { border-left-color: var(--green);  box-shadow: 0 24px 64px rgba(0,0,0,.75), 0 0 32px rgba(0,217,126,.07); }
    .toast.orange { border-left-color: var(--orange); box-shadow: 0 24px 64px rgba(0,0,0,.75), 0 0 32px rgba(255,92,26,.07); }
    .toast.red    { border-left-color: var(--red);    box-shadow: 0 24px 64px rgba(0,0,0,.75), 0 0 32px rgba(255,51,85,.07); }
    .toast.yellow { border-left-color: var(--yellow); }
    .toast.blue   { border-left-color: var(--blue); }
    .toast.purple { border-left-color: var(--purple); }
    .toast-icon   { font-size: 26px; line-height:1; flex-shrink:0; }
    .toast-body   { flex:1; min-width:0; }
    .toast-label  { font-size: 13px; font-weight: 800; letter-spacing:.2px; margin-bottom:3px; }
    .toast.green  .toast-label { color: var(--green); }
    .toast.orange .toast-label { color: var(--orange); }
    .toast.red    .toast-label { color: var(--red); }
    .toast.yellow .toast-label { color: var(--yellow); }
    .toast.blue   .toast-label { color: var(--blue); }
    .toast.purple .toast-label { color: var(--purple); }
    .toast-sub   { font-size: 12px; color: var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .toast-time  { font-size: 10px; color: var(--muted); margin-top: 4px; }
    .toast-close { background:none; border:none; color:var(--muted); cursor:pointer; font-size:16px; padding:0; flex-shrink:0; }
    .toast-close:hover { color:var(--text); }

    /* ════════  RESPONSIVE  ════════ */
    @media (max-width: 1100px) {
      .kpi-grid { grid-template-columns: repeat(3, 1fr); }
    }
    @media (max-width: 768px) {
      body { padding: 10px 11px; }
      .kpi-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
      .growth-section { grid-template-columns: repeat(2, 1fr); gap: 10px; }
      .two-cols   { grid-template-columns: 1fr; }
      .three-cols { grid-template-columns: 1fr; }
      .algo-grid  { grid-template-columns: 1fr; }
      .card { padding: 15px 14px; }
      .kpi-value { font-size: 22px; }
      .brand-name { font-size: 17px; }
      #z-status-inline-row {
        grid-template-columns: 1fr 1fr !important;
        row-gap: 8px;
      }
      #z-status-inline-row > .z-dist-row { grid-column: 1 / -1; text-align: center; padding-left: 0 !important; }
      .rb { padding: 5px 10px; font-size: 10px; }
      #toast-container { right: 10px; top: 10px; }
      .toast { min-width: 260px; }
      .settings-grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 480px) {
      body { padding: 8px 9px; }
      .kpi-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
      .kpi-value { font-size: 20px; }
      .kpi-label { font-size: 8px; letter-spacing: .9px; }
      .kpi-sub { font-size: 9px; }
      .header { padding: 11px 13px; }
      .brand-name { font-size: 15px; }
      .header-right .last-update { display: none; }
      .live-badge { font-size: 10px; padding: 4px 9px; }
      .z-ruler-track { height: 30px; }
      .z-ruler-needle { height: 46px; top: -8px; }
      .z-ruler-needle::after { font-size: 11px; }
    }
  </style>
</head>
<body>
<div id="toast-container"></div>
<div class="shell">

  <!-- ── HEADER ────────────────────────────────────────────────── -->
  <header class="header">
    <div class="brand">
      <!-- Logo: ₿ centrado geométricamente en el cuadrado naranja -->
      <svg width="44" height="44" viewBox="0 0 44 44" fill="none" style="flex-shrink:0">
        <defs>
          <linearGradient id="logoGrad" x1="0" y1="0" x2="44" y2="44" gradientUnits="userSpaceOnUse">
            <stop offset="0%"   stop-color="#ff5c1a"/>
            <stop offset="100%" stop-color="#ff8c42"/>
          </linearGradient>
          <filter id="logoShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="rgba(255,92,26,0.4)"/>
          </filter>
        </defs>
        <!-- Fondo con sombra sutil -->
        <rect width="44" height="44" rx="11" fill="url(#logoGrad)" filter="url(#logoShadow)"/>
        <!-- ₿ centrado: text-anchor + dominant-baseline para centrado perfecto -->
        <text
          x="22"
          y="22"
          font-size="24"
          font-family="'Segoe UI', Arial, sans-serif"
          font-weight="900"
          fill="white"
          text-anchor="middle"
          dominant-baseline="central"
          style="user-select:none">₿</text>
      </svg>
      <div>
        <div class="brand-name">Capital<span>Torreon</span></div>
        <div style="font-size:11px;color:var(--muted);margin-top:2px;letter-spacing:.3px">
          BTC/USDT · MEXC · v7.5
        </div>
      </div>
    </div>
    <div class="header-right">
      <div class="live-badge"><div class="live-dot"></div> EN VIVO</div>
      <div class="last-update" id="last-update-ts">Cargando...</div>
    </div>
  </header>

  <!-- ── KPI CARDS ─────────────────────────────────────────────── -->
  <div class="kpi-grid">
    <div class="kpi-card orange" data-icon="₿">
      <div class="kpi-label">Precio BTC</div>
      <div class="kpi-value" id="kpi-price">—</div>
      <div class="kpi-sub" id="kpi-price-sub">USDT · MEXC</div>
    </div>
    <div class="kpi-card green" data-icon="⚡">
      <div class="kpi-label">Estado Bot</div>
      <div class="kpi-value" id="kpi-state" style="font-size:15px;padding-top:5px">—</div>
      <div class="kpi-sub" id="kpi-state-sub">Posición actual</div>
    </div>
    <div class="kpi-card blue" data-icon="💼">
      <div class="kpi-label">Saldo Cuenta</div>
      <div class="kpi-value" id="kpi-xrp">—</div>
      <div class="kpi-sub" id="kpi-balance-sub">USDT equiv. total</div>
    </div>
    <div class="kpi-card yellow" data-icon="📊">
      <div class="kpi-label">Z-Score</div>
      <div class="kpi-value" id="kpi-z">—</div>
      <div class="kpi-sub" id="kpi-z-sub">vs EMA rápida</div>
    </div>
    <div class="kpi-card purple" data-icon="〜">
      <div class="kpi-label">RSI-8</div>
      <div class="kpi-value" id="kpi-rsi">—</div>
      <div class="kpi-sub" id="kpi-rsi-sub">Momento</div>
    </div>
    <div class="kpi-card red" data-icon="🏆">
      <div class="kpi-label">Win Rate</div>
      <div class="kpi-value" id="kpi-winrate">—</div>
      <div class="kpi-sub" id="kpi-wr-sub">Histórico</div>
    </div>
  </div>

  <!-- ── CRECIMIENTO COMPUESTO ────────────────────────────────── -->
  <div class="growth-section">
    <div class="kpi-card green" id="g-total" data-icon="∞">
      <div class="kpi-label">Crecimiento Total</div>
      <div class="kpi-value" id="g-total-val">—</div>
      <div class="kpi-sub" id="g-total-sub">Desde el inicio</div>
    </div>
    <div class="kpi-card cyan" id="g-24h" data-icon="24">
      <div class="kpi-label">Últimas 24h</div>
      <div class="kpi-value" id="g-24h-val">—</div>
      <div class="kpi-sub" id="g-24h-sub">Rendimiento compuesto</div>
    </div>
    <div class="kpi-card purple" id="g-7d" data-icon="7">
      <div class="kpi-label">Últimos 7 días</div>
      <div class="kpi-value" id="g-7d-val">—</div>
      <div class="kpi-sub" id="g-7d-sub">Rendimiento compuesto</div>
    </div>
    <div class="kpi-card yellow" id="g-30d" data-icon="30">
      <div class="kpi-label">Últimos 30 días</div>
      <div class="kpi-value" id="g-30d-val">—</div>
      <div class="kpi-sub" id="g-30d-sub">Rendimiento compuesto</div>
    </div>
  </div>

  <!-- ── GRÁFICA PRECIO ───────────────────────────────────────── -->
  <div class="main-cols">
    <div class="card c-orange">
      <div class="card-title">
        📈 Precio BTC &amp; Operaciones
        <span class="spinner" id="chart-spinner" style="display:none"></span>
      </div>
      <div class="range-row" id="range-btns">
        <button class="rb-live active" data-range="live"><span class="live-dot"></span>EN VIVO</button>
        <button class="rb" data-range="1h">1H</button>
        <button class="rb" data-range="12h">12H</button>
        <button class="rb" data-range="1d">1D</button>
        <button class="rb" data-range="7d">7D</button>
        <button class="rb" data-range="1m">1M</button>
        <button class="rb" data-range="3m">3M</button>
        <button class="rb" data-range="1y">1A</button>
        <button class="rb" data-range="all">Histórico</button>
        <button class="rb" data-range="equity" style="margin-left:auto;border-color:var(--green);color:var(--green)">📈 Curva Equity</button>
      </div>
      <!-- Stats bar + leyenda (solo en Live) -->
      <div id="live-stats-bar" style="display:block">
        <div class="live-stats-row">
          <div class="live-stat" id="ls-change">
            <span class="ls-label" id="ls-period-label">30 MIN</span>
            <span class="ls-val" id="ls-change-val">—</span>
          </div>
          <div class="live-stat-sep"></div>
          <div class="live-stat">
            <span class="ls-label">MÁXIMO</span>
            <span class="ls-val ls-high" id="ls-high-val">—</span>
          </div>
          <div class="live-stat-sep"></div>
          <div class="live-stat">
            <span class="ls-label">MÍNIMO</span>
            <span class="ls-val ls-low" id="ls-low-val">—</span>
          </div>
          <div class="live-stat-sep"></div>
          <div class="live-stat">
            <span class="ls-label">RANGO</span>
            <span class="ls-val" id="ls-range-val">—</span>
          </div>
          <!-- Leyenda de símbolos -->
          <div class="live-legend">
            <span class="legend-item legend-buy">
              <svg width="12" height="12" viewBox="0 0 12 12">
                <polygon points="6,1 11,11 1,11" fill="#00d97e" stroke="#000" stroke-width="0.8"/>
              </svg>
              Compra
            </span>
            <span class="legend-item legend-sell">
              <svg width="12" height="12" viewBox="0 0 12 12">
                <polygon points="6,11 11,1 1,1" fill="#ff5c1a" stroke="#000" stroke-width="0.8"/>
              </svg>
              Venta
            </span>
            <span class="legend-item legend-stop">
              <svg width="12" height="12" viewBox="0 0 12 12">
                <polygon points="6,11 11,1 1,1" fill="#ff3355" stroke="#000" stroke-width="0.8"/>
              </svg>
              Stop Loss
            </span>
          </div>
        </div>
      </div>
      <!-- Barra de countdown para el modo Live -->
      <div id="live-countdown-wrap">
        <div id="live-countdown-bar-bg"><div id="live-countdown-bar" style="width:100%"></div></div>
        <span id="live-countdown-text">60s</span>
      </div>
      <div id="price-chart" style="width:100%;height:440px"></div>
    </div>
  </div>

  <!-- ── Z-SCORE TIEMPO REAL ────────────────────────────────────── -->
  <div class="main-cols">
    <div class="card c-yellow">
      <div class="card-title">⚡ Z-Score en Tiempo Real</div>

      <!-- Ruler -->
      <div class="z-ruler-wrap">
        <div class="z-ruler-title">POSICIÓN ACTUAL vs SEÑALES DE COMPRA / VENTA</div>
        <div class="z-ruler-track" id="z-ruler-track">
          <span class="z-ruler-zone-label z-ruler-zone-buy">COMPRA</span>
          <span class="z-ruler-zone-label z-ruler-zone-hold">ESPERAR</span>
          <span class="z-ruler-zone-label z-ruler-zone-sell">VENTA</span>
          <div class="z-ruler-needle" id="z-needle" data-z="—" style="left:50%"></div>
        </div>
        <div class="z-ruler-ticks" id="z-ruler-ticks"></div>
      </div>

      <!-- Estado + distancias + mini boxes en la misma fila -->
      <div id="z-status-inline-row" style="display:grid;grid-template-columns:auto 1fr auto auto auto auto;align-items:center;gap:10px;margin-top:14px">
        <div id="z-status-pill" class="z-status-pill hold-zone">ESPERAR</div>
        <div class="z-dist-row" style="padding-left:6px">
          Faltan <span class="z-dist-val" id="z-dist-buy" style="color:#4ade80">—</span> para compra &nbsp;·&nbsp;
          <span class="z-dist-val" id="z-dist-sell" style="color:#fb923c">—</span> para venta
        </div>
        <div class="signal-box">
          <div class="signal-icon">⚙️</div>
          <div class="signal-name">RSI-8</div>
          <div class="signal-val" id="sig-rsi">—</div>
        </div>
        <div class="signal-box">
          <div class="signal-icon">📶</div>
          <div class="signal-name">Z actual</div>
          <div class="signal-val" id="sig-z">—</div>
        </div>
        <div class="signal-box">
          <div class="signal-icon">🎯</div>
          <div class="signal-name">Z Compra</div>
          <div class="signal-val down" id="sig-zbuy">—</div>
        </div>
        <div class="signal-box">
          <div class="signal-icon">🚀</div>
          <div class="signal-name">Z Venta</div>
          <div class="signal-val up" id="sig-zsell">—</div>
        </div>
      </div>
    </div>
  </div>

  <!-- ── CARTERA (ancho completo) ─────────────────────────────── -->
  <div class="card c-blue" style="margin-bottom:var(--gap)">
    <div class="card-title" style="justify-content:space-between;display:flex;align-items:center">
      <span>💼 Cartera · Valor en BTC
        <span style="font-size:11px;color:var(--muted);font-weight:400;margin-left:6px">Últimos 30 días · cortes diarios</span>
      </span>
      <span id="portfolio-today-value" style="font-size:15px;font-weight:800;color:#60a5fa">—</span>
    </div>
    <div id="portfolio-chart" style="width:100%;height:260px"></div>
  </div>

  <!-- ── BALANCE + MÉTRICAS (misma fila) ───────────────────────── -->
  <div class="two-cols">

    <div class="card c-green">
      <div class="card-title">💰 Balance MEXC · Cuenta Main</div>
      <table>
        <thead><tr><th>Activo</th><th class="td-right">Cantidad</th><th class="td-right">Valor USDT</th></tr></thead>
        <tbody id="balances-tbody">
          <tr><td colspan="3" style="color:var(--muted);text-align:center;padding:20px">Cargando...</td></tr>
        </tbody>
      </table>
      <div style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">
        <span style="color:var(--muted);font-size:11px">Total cartera</span>
        <span style="color:#fff;font-size:18px;font-weight:800" id="bal-total">—</span>
      </div>
    </div>

    <div class="card c-purple">
      <div class="card-title">📊 Métricas del Bot</div>
      <table>
        <tbody id="stats-tbody"></tbody>
      </table>
    </div>

  </div>

  <!-- ── ÚLTIMAS 20 OPERACIONES (ancho completo) ───────────────── -->
  <div class="card c-cyan" style="margin-bottom:var(--gap)">
    <div class="card-title">🔄 Últimas 20 Operaciones</div>
    <div style="overflow-x:auto">
      <table>
        <thead>
          <tr>
            <th style="min-width:120px">Tipo</th>
            <th style="min-width:120px">Precio</th>
            <th style="min-width:110px" class="td-right">Ganancia</th>
            <th style="min-width:80px" class="td-right">Z-Score</th>
            <th style="min-width:80px" class="td-right">RSI</th>
            <th style="min-width:160px" class="td-right">Fecha &amp; Hora</th>
          </tr>
        </thead>
        <tbody id="trades-tbody">
          <tr><td colspan="6" style="color:var(--muted);text-align:center;padding:20px">Cargando...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div style="text-align:center;color:rgba(90,100,128,0.6);font-size:10px;padding:8px 0 24px;letter-spacing:.06em;text-transform:uppercase">
    CapitalTorreon v7.5 &nbsp;·&nbsp; MEXC BTC/USDT &nbsp;·&nbsp; 0% Fee MAKER &nbsp;·&nbsp; Stop-Loss 2.0% &nbsp;·&nbsp; Actualiza cada 10s
  </div>

</div>

<script>
// ── Estado global ──────────────────────────────────────────────────────────
let currentRange = '7d';
let liveData = {};

// ── Utils ──────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
function fmtMoney(n, dec=2) {
  if (n == null || isNaN(n)) return '—';
  const parts = Number(n).toFixed(dec).split('.');
  parts[0] = parts[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g, "'");
  return '$' + parts[0] + '.' + (parts[1] || '00');
}
function fmt(n, dec=4) {
  if (n == null || isNaN(n)) return '—';
  const parts = Number(n).toFixed(dec).split('.');
  parts[0] = parts[0].replace(/\\B(?=(\\d{3})+(?!\\d))/g, "'");
  return parts[0] + '.' + (parts[1] || '0000');
}
function fmtPct(n, dec=2) {
  if (n == null || isNaN(n)) return '—';
  return (n >= 0 ? '+' : '') + n.toFixed(dec) + '%';
}
function colorClass(n) {
  if (n == null || isNaN(n)) return '';
  return n > 0 ? 'up' : n < 0 ? 'down' : 'flat';
}

// ── Chart ─────────────────────────────────────────────────────────────────
const LAYOUT = {
  paper_bgcolor:'#020617', plot_bgcolor:'#020617',
  margin:{l:55,r:20,t:10,b:45},
  xaxis:{gridcolor:'#111827',rangeslider:{visible:true,thickness:0.07}},
  yaxis:{gridcolor:'#111827',title:{text:'USD',font:{color:'#6b7280'}}},
  legend:{orientation:'h',x:0.5,xanchor:'center',y:1.05,font:{color:'#e5e7eb',size:11}},
  font:{color:'#e5e7eb'},
  hovermode:'x unified',
};
const CONFIG = { displayModeBar:false, responsive:true };

function renderChart(prices, events) {
  const times  = prices.t || [];
  const priceV = prices.p || [];

  if (times.length === 0) {
    Plotly.newPlot('price-chart', [{
      type:'scatter', mode:'text', x:[0], y:[0],
      text:['Sin datos en este rango'],
      textfont:{size:16, color:'#6b7280'},
    }], {...LAYOUT, xaxis:{visible:false}, yaxis:{visible:false}}, CONFIG);
    return;
  }

  // ── Rango temporal de los precios disponibles ─────────────────────────────
  const tMin = times[0];
  const tMax = times[times.length - 1];

  // ── Filtrar eventos: los eventos YA vienen pre-filtrados por loadChart()
  // (filtro por rango solicitado), aquí solo añadimos que estén dentro del dato disponible.
  // Doble filtro: rango solicitado (loadChart) + dato disponible (aquí).
  const tsMin = new Date(tMin).getTime();
  const tsMax = new Date(tMax).getTime() + 60000;
  const eventsInRange = (events || []).filter(e => {
    const ts = new Date(e.t).getTime();
    return ts >= tsMin && ts <= tsMax;
  });

  // ── Calcular rango Y solo desde los precios (sin markers) ─────────────────
  const hi  = Math.max(...priceV);
  const lo  = Math.min(...priceV);
  const pad = Math.max((hi - lo) * 0.08, 20);  // padding 8% del rango, mínimo $20

  // ── Traza de precio ───────────────────────────────────────────────────────
  const traces = [];
  traces.push({
    type:'scatter', mode:'lines', name:'BTC/USDT',
    x: times, y: priceV,
    line:{ color:'#f97316', width:2 },
    hovertemplate:'$%{y:,.2f}<extra></extra>',
  });

  // ── Agrupar y renderizar markers ──────────────────────────────────────────
  const groups = {};
  for (const ev of eventsInRange) {
    (groups[ev.type] = groups[ev.type] || []).push(ev);
  }

  const evConfig = {
    buy:     { name:'▲ Compra BTC',  color:'#22c55e', symbol:'triangle-up',   size:16, text:'top center' },
    safeBuy: { name:'▲ Compra BTC',  color:'#22c55e', symbol:'triangle-up',   size:16, text:'top center' },
    sell:    { name:'▼ Venta BTC',   color:'#f97316', symbol:'triangle-down', size:16, text:'bottom center' },
    safeSell:{ name:'▼ Venta BTC',   color:'#f97316', symbol:'triangle-down', size:16, text:'bottom center' },
    stopLoss:{ name:'▽ Stop Loss',   color:'#ef4444', symbol:'triangle-down', size:14, text:'bottom center' },
  };

  // Combinar buy+safeBuy y sell+safeSell (mismo tipo visual)
  const merged = {
    buy:      [...(groups.buy||[]),      ...(groups.safeBuy||[])],
    sell:     [...(groups.sell||[]),     ...(groups.safeSell||[])],
    stopLoss: [...(groups.stopLoss||[])],
  };
  const mergedCfg = {
    buy:      evConfig.buy,
    sell:     evConfig.sell,
    stopLoss: evConfig.stopLoss,
  };

  for (const [type, evs] of Object.entries(merged)) {
    if (!evs.length) continue;
    const cfg = mergedCfg[type];
    const priceLabels = evs.map(e =>
      '$' + Number(e.p).toLocaleString('es-MX', {minimumFractionDigits:2, maximumFractionDigits:2}));
    traces.push({
      type:'scatter', mode:'markers+text',
      name: cfg.name,
      x: evs.map(e => e.t),
      y: evs.map(e => e.p),
      text: priceLabels,
      textposition: cfg.text,
      textfont:{ size:9, color: cfg.color, family:'Inter' },
      marker:{
        symbol: cfg.symbol,
        size: cfg.size,
        color: cfg.color,
        line:{ color:'rgba(0,0,0,0.6)', width:1.5 },
        opacity: 0.95,
      },
      hovertemplate: cfg.name + '<br><b>$%{y:,.2f}</b><br>%{x|%H:%M %d/%m}<extra></extra>',
      // Importante: cliponaxis=true para que markers respeten los límites del eje
      cliponaxis: true,
    });
  }

  // ── Layout con ejes fijados al rango de datos ────────────────────────────
  // El rangeslider usa el mismo range que el eje principal → markers no se "escapan"
  const layout = {
    ...LAYOUT,
    xaxis: {
      ...LAYOUT.xaxis,
      range: [tMin, tMax],
      type: 'date',
      fixedrange: false,
      rangeslider: {
        visible: true,
        thickness: 0.07,
        range: [tMin, tMax],   // ← rangeslider también respeta el mismo rango
      },
    },
    yaxis: {
      ...LAYOUT.yaxis,
      range: [lo - pad, hi + pad],
      fixedrange: false,
    },
  };

  Plotly.newPlot('price-chart', traces, layout, CONFIG);
}

function renderEquityChart(curve) {
  const t = curve.map(p => p.t);
  const v = curve.map(p => p.equity);
  const colors = v.map(x => x >= 0 ? '#22c55e' : '#ef4444');
  Plotly.newPlot('price-chart', [{
    type: 'scatter', mode: 'lines+markers', name: 'Crecimiento compuesto %',
    x: t, y: v,
    line:{ color:'#22c55e', width:2 },
    marker:{ size:5, color: colors },
    hovertemplate: '%{y:+.3f}%<extra></extra>',
    fill: 'tozeroy',
    fillcolor: 'rgba(34,197,94,0.07)',
  }], {
    ...LAYOUT,
    yaxis:{ ...LAYOUT.yaxis, title:{text:'Crecimiento %',font:{color:'#6b7280'}},
            tickformat:'+.2f', ticksuffix:'%' },
  }, CONFIG);
}

async function renderPortfolioChart() {
  // Snapshots diarios a las 3:33 PM CDMX + punto de hoy en vivo
  try {
    const pts = await fetch('/CapitalTorreon/api/portfolio')
      .then(r => r.ok ? r.json() : [])
      .catch(() => []);

    if (!pts || pts.length === 0) {
      Plotly.newPlot('portfolio-chart', [{
        type:'scatter', mode:'text', x:[0], y:[0],
        text:['Primer snapshot hoy a las 3:33 PM'],
        textfont:{size:13, color:'#6b7280'},
      }], {...LAYOUT, xaxis:{visible:false}, yaxis:{visible:false}}, CONFIG);
      return;
    }

    const dates = pts.map(p => p.t);
    const vals  = pts.map(p => p.btc_portfolio);   // cartera en BTC
    const live  = pts[pts.length - 1];

    // Actualizar badge con valor actual en BTC
    const todayEl = $('portfolio-today-value');
    if (todayEl && live) {
      todayEl.textContent =
        `${live.btc_portfolio.toFixed(6)} BTC · $${live.usdt_total.toLocaleString('es-MX',{minimumFractionDigits:2})} USDT`;
      todayEl.style.color = '#60a5fa';
    }

    // Colores: gris para histórico, azul para hoy
    const colors = pts.map((p, i) =>
      p.is_live ? '#60a5fa' : (i === pts.length - 1 ? '#60a5fa' : '#334155'));
    const sizes  = pts.map(p => p.is_live ? 10 : 7);

    // Rango Y
    const hi  = Math.max(...vals), lo = Math.min(...vals);
    const pad = Math.max((hi - lo) * 0.15, 0.000005);

    // Traza de barras diarias (más claro para ver cortes)
    const traceBars = {
      type: 'bar',
      x: dates, y: vals,
      name: 'Cartera BTC',
      marker: {
        color: pts.map(p => p.is_live
          ? 'rgba(96,165,250,0.7)'
          : 'rgba(30,58,138,0.55)'),
        line: { color: pts.map(p => p.is_live ? '#60a5fa' : '#1e3a8a'), width: 1 },
      },
      hovertemplate: '<b>%{x}</b><br>%{y:.6f} BTC<extra></extra>',
    };

    // Línea de tendencia sobre las barras
    const traceLine = {
      type: 'scatter', mode: 'lines+markers',
      x: dates, y: vals,
      line: { color: '#3b82f6', width: 1.5, dash: 'dot' },
      marker: { size: sizes, color: colors, line: { color: '#fff', width: 1 } },
      name: 'Tendencia',
      hoverinfo: 'skip',
    };

    Plotly.newPlot('portfolio-chart', [traceBars, traceLine], {
      paper_bgcolor: '#050a14', plot_bgcolor: '#050a14',
      margin: { l:65, r:20, t:10, b:42 },
      barmode: 'overlay',
      xaxis: {
        gridcolor: 'rgba(255,255,255,0.03)', color: '#475569',
        tickfont: { size:10, color:'#475569', family:'Inter' },
        type: 'date', tickformat: '%d %b',
        dtick: pts.length > 14 ? 86400000 * 3 : 86400000,
      },
      yaxis: {
        gridcolor: 'rgba(255,255,255,0.03)', color: '#475569',
        tickfont: { size:10, color:'#475569', family:'Inter' },
        tickformat: '.6f', ticksuffix: ' ₿',
        range: [Math.max(0, lo - pad), hi + pad],
      },
      legend: { orientation:'h', x:.5, xanchor:'center', y:1.06,
                font:{ color:'#94a3b8', size:11 } },
      font: { color:'#e2e8f0', family:'Inter' },
      hovermode: 'x unified',
      hoverlabel: { bgcolor:'rgba(5,10,20,.95)', bordercolor:'rgba(255,255,255,.1)',
                    font:{ color:'#e2e8f0', size:12 } },
    }, { displayModeBar:false, responsive:true });

  } catch(e) { console.error('portfolio chart error', e); }
}

async function refreshBalance() {
  try {
    const b = await fetch('/CapitalTorreon/api/balance').then(r=>r.json());
    if (b.total_usdt != null) {
      // KPI header
      $('kpi-xrp').textContent = fmtMoney(b.total_usdt, 2);
      $('kpi-balance-sub').textContent =
        (b.btc > 0 ? b.btc.toFixed(6) + ' BTC + ' : '') + fmtMoney(b.usdt, 2) + ' USDT';

      // Balance table
      const btcVal = b.btc * b.btc_price;
      const rows = [];
      if (b.btc > 0) {
        rows.push(`<tr>
          <td><span style="color:#f59e0b;font-weight:700">₿ BTC</span></td>
          <td class="td-right" style="font-family:monospace">${b.btc.toFixed(8)}</td>
          <td class="td-right" style="color:#f59e0b;font-weight:600">${fmtMoney(btcVal, 2)}</td>
        </tr>`);
      }
      if (b.usdt > 0) {
        rows.push(`<tr>
          <td><span style="color:#60a5fa;font-weight:700">💵 USDT</span></td>
          <td class="td-right" style="font-family:monospace">${fmtMoney(b.usdt, 2)}</td>
          <td class="td-right" style="color:#60a5fa;font-weight:600">${fmtMoney(b.usdt, 2)}</td>
        </tr>`);
      }
      if (rows.length === 0) {
        rows.push(`<tr><td colspan="3" style="color:var(--muted);text-align:center;padding:16px">Sin saldo disponible</td></tr>`);
      }
      $('balances-tbody').innerHTML = rows.join('');
      if ($('bal-total')) $('bal-total').textContent = fmtMoney(b.total_usdt, 2);
    }
  } catch(e) { console.error('balance error', e); }
  try {
    // El portfolio chart ahora se maneja solo (fetch interno en renderPortfolioChart)
  } catch(e) {}
}

async function loadChart(range) {
  $('chart-spinner').style.display = 'inline-block';
  try {
    if (range === 'equity') {
      const gr = await fetch('/CapitalTorreon/api/growth').then(r=>r.json());
      renderEquityChart(gr.equity_curve || []);
      return;
    }
    const hoursMap  = {'live':0.5,'1h':1,'12h':12,'1d':24,'7d':168,'1m':720,'3m':2160,'1y':8760,'all':9999};
    const labelMap  = {'live':'30 MIN','1h':'1 HORA','12h':'12 HORAS','1d':'1 DÍA',
                       '7d':'7 DÍAS','1m':'1 MES','3m':'3 MESES','1y':'1 AÑO','all':'HISTÓRICO'};
    const hours = hoursMap[range] || 168;
    // Calcular el límite de tiempo SOLICITADO (no el del dato disponible más antiguo)
    const requestedSince = hours < 9999
      ? new Date(Date.now() - hours * 3600 * 1000).getTime()
      : 0;

    const [pr, er] = await Promise.all([
      fetch(`/CapitalTorreon/api/prices/full?hours=${hours}`)
        .then(r => r.ok ? r.json() : fetch('/CapitalTorreon/api/prices?range=' + range).then(r=>r.json()))
        .catch(()=> fetch('/CapitalTorreon/api/prices?range=' + range).then(r=>r.json())),
      fetch('/CapitalTorreon/api/events?range=' + range).then(r=>r.json()),
    ]);

    // Filtrar eventos al RANGO TEMPORAL SOLICITADO (no al dato disponible más antiguo)
    // Esto resuelve el problema con gaps de datos en 1H, 12H, 1D:
    // si la compra fue hace 6 horas pero hay gap de datos, en el gráfico de 1H no debe aparecer.
    const erFiltered = (er || []).filter(e =>
      new Date(e.t).getTime() >= requestedSince
    );

    if (pr.p && pr.p.length > 0) {
      updateStatsBar(pr.p, labelMap[range] || range.toUpperCase());
    }
    renderChart(pr, erFiltered);
  } finally {
    $('chart-spinner').style.display = 'none';
  }
}

// Cargar saldo y cartera al inicio y cada 60s
refreshBalance();
setInterval(refreshBalance, 60000);
// Portfolio chart BTC 30 días
renderPortfolioChart();
setInterval(renderPortfolioChart, 300_000);  // cada 5 min

// ── Stats bar — actualiza los stats del intervalo actual ─────────────────────
function updateStatsBar(prices, periodLabel) {
  if (!prices || prices.length < 2) return;
  const fmt2  = v => '$' + v.toLocaleString('es-MX', {minimumFractionDigits:2, maximumFractionDigits:2});
  const last  = prices[prices.length - 1];
  const first = prices[0];
  const hi    = Math.max(...prices);
  const lo    = Math.min(...prices);
  const delta = last - first;
  const pct   = (delta / first) * 100;
  const isUp  = delta >= 0;

  const lbl = $('ls-period-label');
  const chEl = $('ls-change-val');
  const hiEl = $('ls-high-val');
  const loEl = $('ls-low-val');
  const rng  = $('ls-range-val');

  if (lbl)  lbl.textContent  = periodLabel;
  if (hiEl) hiEl.textContent = fmt2(hi);
  if (loEl) loEl.textContent = fmt2(lo);
  if (rng)  rng.textContent  = fmt2(hi - lo);
  if (chEl) {
    const sign = isUp ? '+' : '';
    chEl.textContent = `${sign}${pct.toFixed(2)}%`;
    chEl.className   = 'ls-val ' + (isUp ? 'ls-up' : 'ls-down');
  }
}

// ── Range buttons (incluye Live, 1H, 12H) ────────────────────────────────────
document.querySelectorAll('.rb, .rb-live').forEach(b => {
  b.addEventListener('click', () => {
    document.querySelectorAll('.rb, .rb-live').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    currentRange = b.dataset.range;
    if (currentRange === 'live') {
      startLiveMode();
    } else {
      stopLiveMode();
      loadChart(currentRange);
    }
  });
});

// ── MODO LIVE ────────────────────────────────────────────────────────────────
let liveInterval     = null;
let countdownTimer   = null;
let countdownSecs    = 60;
const LIVE_REFRESH   = 60;   // segundos entre recargas del chart live
const LIVE_WINDOW_H  = 0.5;  // 30 minutos de histórico

function startLiveMode() {
  stopLiveMode();   // limpiar cualquier loop anterior

  const wrap  = $('live-countdown-wrap');
  if (wrap)  wrap.classList.add('visible');

  // Carga inmediata + cada 60s
  loadLiveChart();
  liveInterval = setInterval(loadLiveChart, LIVE_REFRESH * 1000);

  // Countdown tick cada segundo
  countdownSecs = LIVE_REFRESH;
  updateCountdown();
  countdownTimer = setInterval(updateCountdown, 1000);
}

function stopLiveMode() {
  if (liveInterval)   { clearInterval(liveInterval);   liveInterval   = null; }
  if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; }
  const wrap = $('live-countdown-wrap');
  if (wrap)  wrap.classList.remove('visible');
  // La stats bar NO se oculta — siempre visible en todos los intervalos
}

function updateCountdown() {
  countdownSecs = Math.max(0, countdownSecs - 1);
  const bar  = $('live-countdown-bar');
  const text = $('live-countdown-text');
  const pct  = (countdownSecs / LIVE_REFRESH) * 100;
  if (bar)  bar.style.width  = pct + '%';
  if (text) text.textContent = countdownSecs + 's';
  // Al llegar a 0 el chart ya se recargó vía liveInterval, reiniciar contador
  if (countdownSecs <= 0) countdownSecs = LIVE_REFRESH;
}

async function loadLiveChart() {
  $('chart-spinner').style.display = 'inline-block';
  try {
    const mins = Math.round(LIVE_WINDOW_H * 60);  // 30 min
    const now  = new Date();
    const since = new Date(now - LIVE_WINDOW_H * 3600 * 1000).toISOString();

    // Usar API combinada (triple DB) para los últimos 30 min
    const pr = await fetch(`/CapitalTorreon/api/prices/full?hours=${LIVE_WINDOW_H}`)
      .then(r => r.ok ? r.json() : {t:[], p:[]})
      .catch(() => ({t:[], p:[]}));

    // Eventos de compra/venta en los últimos 30 min
    const er = await fetch('/CapitalTorreon/api/events?range=1d')
      .then(r => r.json()).catch(() => []);

    // Filtrar eventos EXACTAMENTE al rango temporal de los precios recibidos
    // Usar los timestamps de precios como límite absoluto (evita drift de zona horaria)
    const tFirst = pr.t && pr.t.length > 0 ? new Date(pr.t[0]).getTime() : Date.now() - 1800000;
    const tLast  = pr.t && pr.t.length > 0 ? new Date(pr.t[pr.t.length-1]).getTime() : Date.now();
    const evFiltered = er.filter(e => {
      const ts = new Date(e.t).getTime();
      return ts >= tFirst && ts <= tLast + 60000; // +1min de margen para el último punto
    });

    renderLiveChart(pr, evFiltered);
  } finally {
    $('chart-spinner').style.display = 'none';
    // Reiniciar countdown visual
    countdownSecs = LIVE_REFRESH;
  }
}

function renderLiveChart(pr, events) {
  const times  = pr.t || [];
  const prices = pr.p || [];

  // Mostrar/ocultar stats bar
  const statsBar = $('live-stats-bar');
  if (statsBar) statsBar.style.display = times.length > 0 ? 'block' : 'none';

  if (times.length === 0) {
    Plotly.newPlot('price-chart', [], {
      paper_bgcolor:'#050a14', plot_bgcolor:'#050a14',
      margin:{l:55,r:15,t:20,b:40},
      annotations:[{
        text:'Colectando datos — primer minuto en camino…',
        xref:'paper', yref:'paper', x:.5, y:.5, showarrow:false,
        font:{color:'#475569', size:13, family:'Inter'}
      }]
    }, {displayModeBar:false, responsive:true});
    return;
  }

  // ── Métricas de los últimos 30 min ────────────────────────────────────────
  const lastPrice  = prices[prices.length - 1];
  const firstPrice = prices[0];
  const highPrice  = Math.max(...prices);
  const lowPrice   = Math.min(...prices);
  const delta      = lastPrice - firstPrice;
  const deltaPct   = (delta / firstPrice) * 100;
  const range30    = highPrice - lowPrice;
  const isUp       = delta >= 0;
  const color      = isUp ? '#00d97e' : '#ff3355';
  const fillColor  = isUp ? 'rgba(0,217,126,0.07)' : 'rgba(255,51,85,0.07)';

  // Actualizar stats bar con etiqueta "30 MIN"
  updateStatsBar(prices, '30 MIN');

  // ── Traza principal ────────────────────────────────────────────────────────
  // Padding visual: 15% del rango arriba y abajo para que el movimiento se vea bien
  const pad      = Math.max(range30 * 0.15, 20);   // mínimo $20 de padding
  const yMin     = lowPrice  - pad;
  const yMax     = highPrice + pad;

  // Traza con fill "hacia abajo" anclado al yMin (no a $0)
  const traceArea = {
    type: 'scatter', mode: 'none',
    x: [...times, times[times.length-1], times[0]],
    y: [...prices, yMin, yMin],
    fill: 'toself', fillcolor: fillColor,
    showlegend: false, hoverinfo: 'skip',
  };

  const traceLine = {
    type: 'scatter', mode: 'lines',
    x: times, y: prices,
    line: { color, width: 2.2, shape: 'spline', smoothing: 0.6 },
    name: 'BTC/USDT',
    hovertemplate: '<b>$%{y:,.2f}</b><br>%{x|%H:%M:%S}<extra></extra>',
    showlegend: false,
  };

  // ── Punto "ahora" con glow doble ──────────────────────────────────────────
  const traceDot = {
    type: 'scatter', mode: 'markers',
    x: [times[times.length-1]], y: [lastPrice],
    marker: {
      size: [14],
      color: [color],
      opacity: 1,
      line: { color: '#fff', width: 2.5 },
      symbol: 'circle',
    },
    name: 'Precio actual', showlegend: false,
    hovertemplate: `<b>ÚLTIMO PRECIO</b><br><b>$${lastPrice.toLocaleString('es-MX',{minimumFractionDigits:2})}</b><extra></extra>`,
  };

  // ── Operaciones de compra ─────────────────────────────────────────────────
  const groups = {};
  for (const ev of events) { (groups[ev.type] = groups[ev.type]||[]).push(ev); }
  const traceEvents = [];
  const annotations = [];

  const buys  = [...(groups.safeBuy||[]), ...(groups.buy||[])];
  const sells = [...(groups.safeSell||[]), ...(groups.sell||[])];
  const stops = [...(groups.stopLoss||[])];

  if (buys.length > 0) {
    traceEvents.push({
      type:'scatter', mode:'markers+text',
      name:'▲ Compra BTC',
      x: buys.map(e=>e.t), y: buys.map(e=>e.p),
      text: buys.map(e => `$${Number(e.p).toLocaleString('es-MX',{maximumFractionDigits:0})}`),
      textposition: 'bottom center',
      textfont: { size:9, color:'#4ade80', family:'Inter' },
      marker: {
        symbol:'triangle-up', size:18, color:'#00d97e',
        line:{ color:'#022c22', width:1.5 },
        opacity: 0.95,
      },
      hovertemplate: '▲ <b>COMPRA</b><br><b>$%{y:,.2f}</b><br>%{x|%H:%M}<extra></extra>',
      cliponaxis: true,
    });
  }

  if (sells.length > 0) {
    traceEvents.push({
      type:'scatter', mode:'markers+text',
      name:'▼ Venta BTC',
      x: sells.map(e=>e.t), y: sells.map(e=>e.p),
      text: sells.map(e => `$${Number(e.p).toLocaleString('es-MX',{maximumFractionDigits:0})}`),
      textposition: 'top center',
      textfont: { size:9, color:'#fb923c', family:'Inter' },
      marker: {
        symbol:'triangle-down', size:18, color:'#ff5c1a',
        line:{ color:'#431407', width:1.5 },
        opacity: 0.95,
      },
      hovertemplate: '▼ <b>VENTA</b><br><b>$%{y:,.2f}</b><br>%{x|%H:%M}<extra></extra>',
      cliponaxis: true,
    });
  }

  if (stops.length > 0) {
    traceEvents.push({
      type:'scatter', mode:'markers+text',
      name:'🛑 Stop Loss',
      x: stops.map(e=>e.t), y: stops.map(e=>e.p),
      text: stops.map(() => 'SL'),
      textposition: 'top center',
      textfont: { size:8, color:'#f87171', family:'Inter' },
      marker: {
        symbol:'triangle-down', size:16, color:'#ff3355',
        line:{ color:'#4c0519', width:1.5 },
        opacity: 0.95,
      },
      hovertemplate: '🛑 <b>STOP LOSS</b><br><b>$%{y:,.2f}</b><br>%{x|%H:%M}<extra></extra>',
      cliponaxis: true,
    });
  }

  // ── Anotación del precio actual flotante ──────────────────────────────────
  const sign30  = isUp ? '+' : '';
  const priceLbl = lastPrice.toLocaleString('es-MX', {minimumFractionDigits:2});
  const deltaLbl = `${sign30}${deltaPct.toFixed(2)}%  ${sign30}$${Math.abs(delta).toFixed(2)}`;

  annotations.push({
    x: times[times.length-1], y: lastPrice,
    xref:'x', yref:'y',
    text: `<b>$${priceLbl}</b>  <span style="font-size:11px">${deltaLbl}</span>`,
    showarrow: true,
    arrowhead: 0, arrowwidth: 1.5, arrowcolor: color,
    ax: -110, ay: -28,
    bgcolor: 'rgba(5,10,20,0.92)',
    bordercolor: color, borderwidth: 1.5, borderpad: 6,
    font: { color: color, size: 13, family: 'Inter', },
    align: 'left',
  });

  // ── Shapes: línea horizontal del precio actual + banda high/low ───────────
  const shapes = [
    {
      type:'line', xref:'paper', yref:'y',
      x0:0, x1:1, y0:lastPrice, y1:lastPrice,
      line: { color, width:1, dash:'dot' },
    },
    {
      // Banda de rango del período (muy sutil)
      type:'rect', xref:'paper', yref:'y',
      x0:0, x1:1, y0:lowPrice, y1:highPrice,
      fillcolor: isUp ? 'rgba(0,217,126,0.025)' : 'rgba(255,51,85,0.025)',
      line: { width:0 },
      layer: 'below',
    },
  ];

  const layout = {
    paper_bgcolor: '#050a14',
    plot_bgcolor:  '#050a14',
    margin: { l:60, r:20, t:16, b:42 },
    xaxis: {
      gridcolor: 'rgba(255,255,255,0.035)',
      color: '#475569',
      tickfont: { size:10, color:'#475569', family:'Inter' },
      type: 'date',
      tickformat: '%H:%M',
      // ← FIJO al primer y último timestamp de precios: markers no expanden el eje
      range: [times[0], times[times.length - 1]],
      showspikes: true, spikecolor: 'rgba(255,255,255,0.15)',
      spikethickness: 1, spikedash: 'dot', spikemode: 'across',
    },
    yaxis: {
      gridcolor: 'rgba(255,255,255,0.035)',
      color: '#475569',
      tickfont: { size:10, color:'#475569', family:'Inter' },
      tickformat: '$,',
      tickprefix: '',
      range: [yMin, yMax],
      showspikes: true, spikecolor: 'rgba(255,255,255,0.15)',
      spikethickness: 1,
    },
    legend: {
      orientation:'h', x:.5, xanchor:'center', y:-0.12,
      font:{ color:'#94a3b8', size:11, family:'Inter' },
      bgcolor:'rgba(0,0,0,0)',
      traceorder: 'normal',
    },
    font: { color:'#e2e8f0', family:'Inter' },
    annotations,
    shapes,
    hovermode: 'x unified',
    hoverlabel: {
      bgcolor:'rgba(5,10,20,0.95)',
      bordercolor:'rgba(255,255,255,0.1)',
      font:{ color:'#e2e8f0', size:12, family:'Inter' },
    },
    transition: { duration: 400, easing: 'cubic-in-out' },
  };

  // useResizeObserver para animación suave al actualizar
  const existing = document.getElementById('price-chart')._fullLayout;
  const traces = [traceArea, traceLine, traceDot, ...traceEvents];
  if (existing) {
    Plotly.react('price-chart', traces, layout, { displayModeBar:false, responsive:true });
  } else {
    Plotly.newPlot('price-chart', traces, layout, { displayModeBar:false, responsive:true });
  }
}

// ── Live data ─────────────────────────────────────────────────────────────
async function refreshLive() {
  try {
    const d = await fetch('/CapitalTorreon/api/live').then(r=>r.json());
    liveData = d;

    // Precio
    if (d.price != null) {
      $('kpi-price').textContent = fmtMoney(d.price, 2);
    }

    // Estado
    const isXrp = d.state === 'HOLD_TRADE_XRP';
    $('kpi-state').innerHTML = isXrp
      ? '<span class="state-badge state-xrp">● HOLD BTC</span>'
      : '<span class="state-badge state-usd">● HOLD USD</span>';
    $('kpi-state-sub').textContent = isXrp ? 'Acumulando BTC' : 'Esperando retroceso';

    // XRP total
    if (d.total_xrp) $('kpi-xrp').textContent = fmt(d.total_xrp, 4);

    // Z-score
    const z = d.z_score;
    $('kpi-z').textContent = z != null ? z.toFixed(3) : '—';
    $('kpi-z').className = 'kpi-value ' + (z > 0 ? 'up' : z < 0 ? 'down' : '');
    $('sig-z').textContent = z != null ? z.toFixed(3) : '—';
    $('sig-z').className = 'signal-val ' + (z > 0 ? 'up' : z < 0 ? 'down' : 'flat');

    // RSI
    const rsi = d.rsi;
    $('kpi-rsi').textContent = rsi != null ? rsi.toFixed(1) : '—';
    $('kpi-rsi-sub').textContent = rsi > 60 ? 'Sobrecompra' : rsi < 40 ? 'Sobreventa' : 'Neutral';
    $('sig-rsi').textContent = rsi != null ? rsi.toFixed(1) : '—';
    $('sig-rsi').className = 'signal-val ' + (rsi > 60 ? 'up' : rsi < 40 ? 'down' : 'flat');

    // Z thresholds de settings
    const zbuy  = parseFloat(d.settings?.Z_BUY  || '-1.8');
    const zsell = parseFloat(d.settings?.Z_SELL || '1.8');
    $('sig-zbuy').textContent  = zbuy.toFixed(3);
    $('sig-zsell').textContent = zsell.toFixed(3);

    // ── Z-Score Ruler ──────────────────────────────────────────────
    if (z != null) {
      // El ruler cubre [zbuy - 0.5 .. zsell + 0.5] para dar contexto
      const rulerMin = zbuy - 0.5;
      const rulerMax = zsell + 0.5;
      const rulerSpan = rulerMax - rulerMin;

      // Posición del needle como % del ancho del track
      const needlePct = Math.min(99, Math.max(1, ((z - rulerMin) / rulerSpan) * 100));
      const needle = $('z-needle');
      needle.style.left = needlePct + '%';
      needle.setAttribute('data-z', (z >= 0 ? '+' : '') + z.toFixed(3));

      // Ticks: min, zbuy, 0, zsell, max
      const tickVals = [
        { v: rulerMin, cls: '' },
        { v: zbuy,     cls: 'threshold-buy'  },
        { v: 0,        cls: 'zero'            },
        { v: zsell,    cls: 'threshold-sell'  },
        { v: rulerMax, cls: '' },
      ];
      const ticksEl = $('z-ruler-ticks');
      ticksEl.innerHTML = tickVals.map(t =>
        `<span class="z-ruler-tick ${t.cls}">${(t.v >= 0 ? '+' : '') + t.v.toFixed(2)}</span>`
      ).join('');

      // Estado + distancias
      const distToBuy  = (z - zbuy).toFixed(3);   // positivo = aún no llega
      const distToSell = (zsell - z).toFixed(3);  // positivo = falta para llegar
      const pill = $('z-status-pill');
      if (z <= zbuy) {
        pill.textContent = '🟢 ZONA DE COMPRA';
        pill.className = 'z-status-pill buy-zone';
      } else if (z >= zsell) {
        pill.textContent = '🔴 ZONA DE VENTA';
        pill.className = 'z-status-pill sell-zone';
      } else {
        pill.textContent = '⏸ ZONA NEUTRAL';
        pill.className = 'z-status-pill hold-zone';
      }
      $('z-dist-buy').textContent  = z <= zbuy  ? '¡YA!' : '+' + distToBuy  + 'σ';
      $('z-dist-sell').textContent = z >= zsell ? '¡YA!' : '+' + distToSell + 'σ';
    }

    // Balances
    const bal = d.balances || {};
    const growth = d.growth || {};
    const tbody = $('balances-tbody');
    if (Object.keys(bal).length > 0) {
      tbody.innerHTML = Object.entries(bal).map(([acc, v]) => {
        const g = growth[acc] ?? 0;
        return `<tr>
          <td style="font-weight:600">${acc}</td>
          <td>${fmt(v.current, 6)} BTC</td>
          <td class="td-right" style="color:${g>=0?'var(--green)':'var(--red)'}">${fmtPct(g)}</td>
        </tr>`;
      }).join('');
    }

    // Settings
    const sGrid = $('settings-grid');
    const sKeys = {
      'TRADE_PCT':'Trade %','Z_BUY':'Z Compra','Z_SELL':'Z Venta',
      'EMA_FAST_MINUTES':'EMA Rápida','EMA_SLOW_MINUTES':'EMA Lenta',
      'STD_WINDOW_MINUTES':'Ventana STD','COOLDOWN_MINUTES':'Cooldown',
      'GOAL_ASSET':'Objetivo','Z_SELL_TURBO':'Z Turbo','EXTRA_SELL_PCT':'Extra Sell %',
    };
    sGrid.innerHTML = Object.entries(sKeys).map(([k, label]) => {
      const v = d.settings?.[k] ?? '—';
      return `<div class="setting-item"><span class="setting-key">${label}</span><span class="setting-val">${v}</span></div>`;
    }).join('');

    // Timestamp
    const now = new Date();
    $('last-update-ts').textContent = 'Actualizado: ' + now.toLocaleTimeString('es-MX');

  } catch(e) {
    console.error('live refresh error', e);
  }
}

async function refreshStats() {
  try {
    const d = await fetch('/CapitalTorreon/api/stats').then(r=>r.json());

    $('kpi-winrate').textContent = d.win_rate != null ? d.win_rate.toFixed(1) + '%' : '—';
    $('kpi-wr-sub').textContent = d.wins + ' ganancias / ' + d.losses + ' pérdidas';

    $('stats-tbody').innerHTML = [
      ['Total Trades', d.total_trades],
      ['Compras', d.total_buys],
      ['Ventas', d.total_sells],
      ['Ganancia promedio/trade', fmtPct(d.avg_profit_pct, 3)],
      ['Win Rate', d.win_rate + '%'],
    ].map(([k,v]) => `<tr><td style="color:var(--muted)">${k}</td><td class="td-right" style="font-weight:700">${v}</td></tr>`).join('');

  } catch(e) {}
}

async function refreshGrowth() {
  try {
    const d = await fetch('/CapitalTorreon/api/growth').then(r=>r.json());
    const periods = [
      { key:'total', valId:'g-total-val', subId:'g-total-sub', label:'desde el inicio' },
      { key:'24h',   valId:'g-24h-val',  subId:'g-24h-sub',  label:'últimas 24h' },
      { key:'7d',    valId:'g-7d-val',   subId:'g-7d-sub',   label:'últimos 7 días' },
      { key:'30d',   valId:'g-30d-val',  subId:'g-30d-sub',  label:'últimos 30 días' },
    ];
    for (const p of periods) {
      const m = d[p.key];
      if (!m) continue;
      const pct = m.growth_pct;
      const el = $(p.valId);
      el.textContent = (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%';
      el.className = 'kpi-value ' + (pct > 0 ? 'growth-up' : pct < 0 ? 'growth-down' : '');
      $(p.subId).textContent = m.cycles + ' ciclos · ' + p.label;
    }
  } catch(e) { console.error('growth refresh error', e); }
}

async function refreshTrades() {
  try {
    const evs = await fetch('/CapitalTorreon/api/events?range=all').then(r=>r.json());
    const last20 = evs.slice(-20).reverse();
    const typeLabel = {
      buy:'🟢 Compra BTC', safeBuy:'🟢 Compra BTC', sell:'🔴 Venta BTC',
      safeSell:'🔴 Venta BTC', stopLoss:'🛑 Stop Loss', deposit:'💵 Depósito'
    };
    const typeColor = {
      buy:'var(--green)', safeBuy:'var(--green)', sell:'var(--orange)',
      safeSell:'var(--orange)', stopLoss:'var(--red)', deposit:'var(--blue)'
    };
    const tbody = $('trades-tbody');
    if (last20.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="color:var(--muted);text-align:center;padding:24px">
        Sin operaciones registradas — el bot ejecutará su primera cuando cruce el umbral Z
      </td></tr>`;
      return;
    }

    // Emparejar compras con ventas para calcular ganancia
    const paired = [];
    let lastBuy = null;
    for (const e of [...evs].sort((a,b) => a.t.localeCompare(b.t))) {
      if (e.type === 'buy' || e.type === 'safeBuy') { lastBuy = e; }
      else if ((e.type === 'sell' || e.type === 'safeSell') && lastBuy) {
        paired.push({ sell: e, buy: lastBuy, gain: e.p - lastBuy.p, pct: (e.p/lastBuy.p-1)*100 });
        lastBuy = null;
      }
    }
    const gainMap = {};
    for (const p of paired) { gainMap[p.sell.t] = p; }

    function timeAgo(dateStr) {
      const diff = (Date.now() - new Date(dateStr)) / 1000;
      if (diff < 60)    return Math.round(diff) + 's';
      if (diff < 3600)  return Math.round(diff/60) + 'min';
      if (diff < 86400) return Math.round(diff/3600) + 'h';
      return Math.round(diff/86400) + 'd';
    }

    tbody.innerHTML = last20.map(e => {
      const d = new Date(e.t);
      const isBuy     = e.type === 'buy' || e.type === 'safeBuy';
      const isStop    = e.type === 'stopLoss';
      const isDeposit = e.type === 'deposit';
      const col = typeColor[e.type] || 'var(--text)';

      // ── Depósito: fila especial, sin ganancia/Z/RSI ──────────────────────
      if (isDeposit) {
        const dd = new Date(e.t);
        const fecha = `${dd.getFullYear()}_${String(dd.getMonth()+1).padStart(2,'0')}_${String(dd.getDate()).padStart(2,'0')}&nbsp;${String(dd.getHours()).padStart(2,'0')}_${String(dd.getMinutes()).padStart(2,'0')}_${String(dd.getSeconds()).padStart(2,'0')}`;
        return `<tr style="background:rgba(59,130,246,0.06);border-left:3px solid var(--blue)">
          <td style="color:var(--blue);font-weight:700;font-size:13px">💵 Depósito USDT</td>
          <td style="font-weight:800;font-size:14px;color:#60a5fa;font-variant-numeric:tabular-nums">
            +$${Number(e.p).toLocaleString('es-MX',{minimumFractionDigits:2,maximumFractionDigits:2})}
          </td>
          <td class="td-right" style="color:var(--muted);font-size:11px;font-style:italic">Capital externo</td>
          <td class="td-right" style="color:var(--muted)">—</td>
          <td class="td-right" style="color:var(--muted)">—</td>
          <td class="td-right" style="color:var(--muted);font-size:12px;font-family:monospace">${fecha}</td>
        </tr>`;
      }

      const rowClass = isBuy ? 'trade-row-buy' : isStop ? 'trade-row-stop' : 'trade-row-sell';

      // Ganancia (solo para ventas emparejadas)
      let gainCell = '<td class="td-right" style="color:var(--muted);font-size:12px">—</td>';
      if (!isBuy && gainMap[e.t]) {
        const g = gainMap[e.t];
        const gc = g.pct >= 0 ? 'var(--green)' : 'var(--red)';
        const gs = g.pct >= 0 ? '+' : '';
        gainCell = `<td class="td-right" style="color:${gc};font-weight:700;font-size:12px">
          ${gs}${g.pct.toFixed(3)}%<br>
          <span style="font-size:10px;font-weight:400">${gs}$${Math.abs(g.gain).toFixed(2)}</span>
        </td>`;
      } else if (isBuy) {
        gainCell = `<td class="td-right" style="color:var(--muted);font-size:11px">Entrada</td>`;
      }

      // Z-score y RSI: ya vienen parseados desde Python en el campo e.z / e.rsi
      const zVal   = e.z   != null ? Number(e.z).toFixed(3)   : '—';
      const rsiVal = e.rsi != null ? Number(e.rsi).toFixed(1) : '—';
      const zColor = e.z != null
        ? (e.z < 0 ? 'var(--green)' : 'var(--orange)')
        : 'var(--muted)';

      return `<tr class="${rowClass}">
        <td style="color:${col};font-weight:700;font-size:13px">${typeLabel[e.type] || e.type}</td>
        <td style="font-weight:700;font-variant-numeric:tabular-nums">
          $${Number(e.p).toLocaleString('es-MX',{minimumFractionDigits:2,maximumFractionDigits:2})}
        </td>
        ${gainCell}
        <td class="td-right" style="color:${zColor};font-size:12px;font-variant-numeric:tabular-nums;font-family:monospace">${zVal}</td>
        <td class="td-right" style="color:var(--muted);font-size:12px">${rsiVal}</td>
        <td class="td-right" style="color:var(--muted);font-size:12px;font-family:monospace;letter-spacing:.3px">
          ${d.getFullYear()}_${String(d.getMonth()+1).padStart(2,'0')}_${String(d.getDate()).padStart(2,'0')}&nbsp;
          ${String(d.getHours()).padStart(2,'0')}_${String(d.getMinutes()).padStart(2,'0')}_${String(d.getSeconds()).padStart(2,'0')}
        </td>
      </tr>`;
    }).join('');
  } catch(err) { console.error('trades error', err); }
}

// ── Toast notifications ────────────────────────────────────────────────────
const TOAST_THEMES = {
  green:  '#22c55e', orange: '#f97316', yellow: '#eab308',
  blue:   '#3b82f6', red:    '#ef4444', purple: '#a855f7',
};

function showToast({ emoji, label, theme, subtitle, time }) {
  const container = $('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${theme}`;

  const timeStr = time
    ? new Date(time).toLocaleTimeString('es-MX', {hour:'2-digit', minute:'2-digit', second:'2-digit'})
    : new Date().toLocaleTimeString('es-MX', {hour:'2-digit', minute:'2-digit', second:'2-digit'});

  el.innerHTML = `
    <div class="toast-icon">${emoji}</div>
    <div class="toast-body">
      <div class="toast-label">${label}</div>
      ${subtitle ? `<div class="toast-sub">${subtitle}</div>` : ''}
      <div class="toast-time">${timeStr}</div>
    </div>
    <button class="toast-close" onclick="this.closest('.toast').remove()">✕</button>
  `;

  container.appendChild(el);
  // Remove after animation completes (3s)
  setTimeout(() => el.remove(), 3100);
}

// Track the latest notification timestamp seen
let lastNotifTs = new Date().toISOString();  // Start from NOW — skip history

async function pollNotifications() {
  try {
    const url = '/CapitalTorreon/api/notifications?since=' + encodeURIComponent(lastNotifTs);
    const items = await fetch(url).then(r => r.json());
    if (!Array.isArray(items) || items.length === 0) return;

    for (const item of items) {
      showToast({
        emoji:    item.emoji,
        label:    item.label,
        theme:    item.theme,
        subtitle: item.subtitle,
        time:     item.t,
      });
    }
    // Advance cursor to the newest event seen
    lastNotifTs = items[items.length - 1].t;
  } catch(e) {
    // Silently ignore — notifications are best-effort
  }
}

// ── Init — Live es la vista default ──────────────────────────────────────────
(async function init() {
  // Arrancar en modo Live (vista default al entrar)
  currentRange = 'live';

  await Promise.all([
    startLiveMode(),        // Live chart con countdown
    refreshLive(),          // KPIs
    refreshStats(),
    refreshTrades(),
    refreshGrowth(),
  ]);

  // Auto-refresh de KPIs y datos (independiente del chart)
  setInterval(refreshLive,          10_000);
  setInterval(refreshStats,         60_000);
  setInterval(refreshTrades,        30_000);
  setInterval(refreshGrowth,       120_000);
  setInterval(pollNotifications,     5_000);
})();
</script>
</body>
</html>
"""
