"""Rayos X Inscripciones — FastAPI app."""
from __future__ import annotations
import json
import os
import re
from datetime import datetime
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session

from .database import init_db, get_db, DiagnosticSession, make_short_code
from .services.diagnosis_engine import run_diagnosis, compute_funnel_metrics
from .services.pdf_service import generate_client_pdf, generate_internal_pdf

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# ── Access control ────────────────────────────────────────────────────────────
# Set RAYOSX_PIN environment variable to change the access code.
ACCESS_PIN = os.environ.get("RAYOSX_PIN", "SL-RX-2025")

def _pin_ok(pin: str) -> bool:
    return pin.strip() == ACCESS_PIN


# ── Security headers middleware ───────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Robots-Tag"]                = "noindex, nofollow"
        response.headers["X-Frame-Options"]             = "DENY"
        response.headers["X-Content-Type-Options"]      = "nosniff"
        response.headers["Referrer-Policy"]             = "no-referrer"
        return response


app = FastAPI(title="Rayos X Inscripciones", docs_url=None, redoc_url=None)
app.add_middleware(SecurityHeadersMiddleware)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# ── CapitalTorreon XRP Bot Dashboard ─────────────────────────────────────────
from .capitaltorreon import router as ct_router
app.include_router(ct_router)

# ── Redirect: torreonCapital.superleads.mx → /CapitalTorreon ─────────────────
# Cuando el host sea torreonCapital.superleads.mx y la ruta sea / o vacía,
# redirigir directamente al dashboard. Así la URL queda limpia sin path.
@app.middleware("http")
async def capital_torreon_redirect(request: Request, call_next):
    host = request.headers.get("host", "").lower().split(":")[0]
    if "torneoncapital" in host or "torreon" in host:
        path = request.url.path
        if path in ("", "/", "/CapitalTorreon"):
            if path != "/CapitalTorreon/":
                return RedirectResponse("/CapitalTorreon/", status_code=301)
    return await call_next(request)

PREFIX = ""
OLD_PREFIX = "/Rayos_X_inscripciones"  # backward-compat redirect


@app.on_event("startup")
def startup():
    init_db()
    os.makedirs(os.path.join(STATIC_DIR, "pdfs"), exist_ok=True)
    os.makedirs(os.path.join(STATIC_DIR, "img"), exist_ok=True)


def _get_session_or_404(session_id: str, db: Session) -> DiagnosticSession:
    s = db.query(DiagnosticSession).filter(DiagnosticSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return s


def _tr(request: Request, name: str, ctx: dict = None):
    """Wrapper compatible with Starlette 1.0 TemplateResponse."""
    context = ctx or {}
    try:
        # Starlette 1.0+: request is first positional arg, not in context
        return templates.TemplateResponse(request, name, context)
    except TypeError:
        # Fallback for older starlette
        context["request"] = request
        return templates.TemplateResponse(name, context)


# ─── Landing ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request, error: str = ""):
    return _tr(request, "rayosx/landing.html", {
        "pin_error":     error == "pin",
        "session_error": error == "session",
        "prefix":        PREFIX,
    })


# ─── Backward-compat redirects (old URL → root) ──────────────────────────────

@app.get(OLD_PREFIX)
@app.get(OLD_PREFIX + "/")
async def legacy_root():
    return RedirectResponse("/", status_code=301)


@app.get(OLD_PREFIX + "/{rest:path}")
async def legacy_path(rest: str):
    return RedirectResponse(f"/{rest}", status_code=301)


# ─── Start new session ────────────────────────────────────────────────────────

@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    return "User-agent: *\nDisallow: /\n"


@app.post(PREFIX + "/start")
async def start_session(db: Session = Depends(get_db)):
    s = DiagnosticSession(short_code=make_short_code())
    db.add(s)
    db.commit()
    db.refresh(s)
    return RedirectResponse(f"{PREFIX}/paso/1/{s.id}", status_code=303)


@app.post(PREFIX + "/recuperar")
async def recover_session(
    session_code: str = Form(""),
    db: Session = Depends(get_db)
):
    """Recover an existing session by short_code — no PIN required."""
    code = session_code.strip().upper()
    if not code:
        return RedirectResponse(f"{PREFIX}?error=session", status_code=303)
    s = db.query(DiagnosticSession).filter(DiagnosticSession.short_code == code).first()
    if not s:
        return RedirectResponse(f"{PREFIX}?error=session", status_code=303)
    if s.status == "analyzed":
        return RedirectResponse(f"{PREFIX}/resultados/{s.id}", status_code=303)
    return RedirectResponse(f"{PREFIX}/revision/{s.id}", status_code=303)


# ─── Steps ────────────────────────────────────────────────────────────────────

STEPS = [
    (1, "Identidad de la institución", "identity"),
    (2, "Números del embudo", "funnel"),
    (3, "Velocidad y contactación", "velocity"),
    (4, "Canales y estructura", "channels"),
    (5, "Calidad y mercado", "market"),
]

STEP_TEMPLATES = {
    1: "rayosx/step_identity.html",
    2: "rayosx/step_funnel.html",
    3: "rayosx/step_velocity.html",
    4: "rayosx/step_channels.html",
    5: "rayosx/step_market.html",
}


def _step_ctx(step: int, session: DiagnosticSession, answers: dict) -> dict:
    return {
        "step": step,
        "total_steps": len(STEPS),
        "step_name": STEPS[step - 1][1],
        "session_id": session.id,
        "short_code": session.short_code,
        "answers": answers,
        "progress_pct": int((step - 1) / len(STEPS) * 100),
        "prefix": PREFIX,
    }


@app.get(PREFIX + "/paso/{step}/{session_id}", response_class=HTMLResponse)
async def get_step(request: Request, step: int, session_id: str, db: Session = Depends(get_db)):
    if step < 1 or step > len(STEPS):
        return RedirectResponse(PREFIX)
    session = _get_session_or_404(session_id, db)
    answers = session.get_answers()
    return _tr(request, STEP_TEMPLATES[step], _step_ctx(step, session, answers))


# Checkboxes por paso: si el usuario los desmarca no viajan en el form,
# así que hay que limpiar los valores guardados antes de re-aplicar.
_CHECKBOX_PREFIXES = {
    3: ("easy_scheduling", "can_advance_online", "can_pay_online",
        "automated_followup", "sched_"),
    4: ("ch_",),
    5: ("obj_", "loss_"),
}


@app.post(PREFIX + "/paso/{step}/{session_id}")
async def post_step(request: Request, step: int, session_id: str, db: Session = Depends(get_db)):
    session = _get_session_or_404(session_id, db)
    form = await request.form()
    answers = session.get_answers()

    # Limpiar checkboxes rancios de este paso antes de aplicar el form
    for prefix in _CHECKBOX_PREFIXES.get(step, ()):
        for key in [k for k in answers if k.startswith(prefix)]:
            del answers[key]

    for key, value in form.items():
        if key.startswith("_"):
            continue
        answers[key] = str(value).strip()

    # ── Paso 2: embudo en CASCADA — cada % es sobre la etapa anterior ─────
    #   leads → ×contact% → contactados → ×cita% → citas → ×asistencia% →
    #   asistentes → ×cierre% → inscritos (estimado)
    #   Si el usuario dio inscritos reales, ese número manda; la estimación
    #   queda guardada aparte para mostrar la coherencia.
    if step == 2:
        try:
            daily          = int(answers.get("daily_conversations") or 0)
            leads_year     = daily * 365
            enrolled_total = int(answers.get("enrolled_total") or 0)
            contact_pct    = int(answers.get("contact_pct") or 60)
            appt_pct       = int(answers.get("appointment_pct") or 40)
            att_pct        = int(answers.get("attendance_pct") or 70)
            close_pct      = int(answers.get("close_pct") or 50)

            if leads_year > 0:
                contacted    = leads_year * contact_pct // 100
                appointments = contacted * appt_pct // 100
                attended     = appointments * att_pct // 100
                enrolled_est = attended * close_pct // 100

                answers["leads"]              = str(leads_year)
                answers["contacted"]          = str(contacted)
                answers["appointments"]       = str(appointments)
                answers["attended"]           = str(attended)
                answers["enrolled_estimated"] = str(enrolled_est)
                answers["funnel_pct_mode"]    = "cascade"

                if enrolled_total > 0:
                    answers["enrolled"] = str(enrolled_total)
                    if attended > 0:
                        answers["implied_close_pct"] = str(round(enrolled_total / attended * 100))
                else:
                    answers["enrolled"] = str(enrolled_est)
            elif enrolled_total > 0:
                answers["enrolled"] = str(enrolled_total)
        except (ValueError, TypeError):
            pass

    # ── Paso 3: combinar horarios de atención (multi-select) ─────────────
    if step == 3:
        sched = [code for code, key in [
            ("horario_oficina", "sched_oficina"),
            ("horario_ampliado", "sched_tarde"),
            ("fines_semana", "sched_finde"),
            ("24_7", "sched_247"),
        ] if answers.get(key) == "si"]
        if sched:
            answers["lead_attention_schedule"] = ",".join(sched)

    # ── Paso 5: combinar objeciones y razones de pérdida (multi-select) ──
    if step == 5:
        objs = [answers[k] for k in sorted(answers) if k.startswith("obj_") and answers.get(k)]
        if objs or answers.get("top_2_objections_text"):
            full = objs + ([answers["top_2_objections_text"]] if answers.get("top_2_objections_text") else [])
            answers["objections_list"] = " | ".join(full)

        losses = [answers[k] for k in sorted(answers) if k.startswith("loss_") and answers.get(k)]
        if losses:
            answers["primary_loss_reason"] = losses[0]
            answers["loss_reasons"] = ",".join(losses)

    session.set_answers(answers)
    session.updated_at = datetime.utcnow()
    db.commit()

    next_step = step + 1
    if next_step > len(STEPS):
        return RedirectResponse(f"{PREFIX}/revision/{session_id}", status_code=303)
    return RedirectResponse(f"{PREFIX}/paso/{next_step}/{session_id}", status_code=303)


# ─── Review ───────────────────────────────────────────────────────────────────

@app.get(PREFIX + "/revision/{session_id}", response_class=HTMLResponse)
async def revision(request: Request, session_id: str, db: Session = Depends(get_db)):
    session = _get_session_or_404(session_id, db)
    answers = session.get_answers()
    return _tr(request, "rayosx/review.html", {
        "session_id": session_id,
        "short_code": session.short_code,
        "answers": answers,
        "steps": STEPS,
        "prefix": PREFIX,
    })


# ─── Analyze ─────────────────────────────────────────────────────────────────

@app.post(PREFIX + "/analizar/{session_id}")
async def analyze(session_id: str, db: Session = Depends(get_db)):
    _get_session_or_404(session_id, db)
    return RedirectResponse(f"{PREFIX}/analizando/{session_id}", status_code=303)


@app.get(PREFIX + "/analizando/{session_id}", response_class=HTMLResponse)
async def analyzing_page(request: Request, session_id: str):
    return _tr(request, "rayosx/analyzing.html", {
        "session_id": session_id,
        "prefix": PREFIX,
    })


@app.get(PREFIX + "/run-analysis/{session_id}")
async def run_analysis(session_id: str, db: Session = Depends(get_db)):
    """Called by JS after animation completes."""
    session = _get_session_or_404(session_id, db)
    answers = session.get_answers()

    result = run_diagnosis(answers)

    session.set_findings(result["findings"])
    session.completeness_score = result["completeness_score"]
    session.certainty_score = result["certainty_score"]
    session.analyzed_at = datetime.utcnow()
    session.status = "analyzed"

    try:
        client_path = generate_client_pdf(session, answers, result)
        session.pdf_client_path = client_path
    except Exception as e:
        print(f"PDF client error: {e}")

    try:
        internal_path = generate_internal_pdf(session, answers, result)
        session.pdf_internal_path = internal_path
    except Exception as e:
        print(f"PDF internal error: {e}")

    db.commit()
    return {"ok": True, "redirect": f"{PREFIX}/resultados/{session_id}"}


# ─── Results ─────────────────────────────────────────────────────────────────

@app.get(PREFIX + "/resultados/{session_id}", response_class=HTMLResponse)
async def results(request: Request, session_id: str, db: Session = Depends(get_db)):
    session = _get_session_or_404(session_id, db)
    if session.status != "analyzed":
        return RedirectResponse(f"{PREFIX}/analizando/{session_id}")
    answers = session.get_answers()
    findings = session.get_findings()
    metrics = compute_funnel_metrics(answers)
    # Recalcular el total recuperable (no se persiste; barato de computar)
    from .services.diagnosis_engine import _compute_total_recoverable, _load_rules
    _bench = _load_rules().get("benchmarks", {})
    total_recoverable = _compute_total_recoverable(metrics, _bench) if _bench else {}

    return _tr(request, "rayosx/results.html", {
        "session": session,
        "answers": answers,
        "findings": findings,
        "metrics": metrics,
        "total_recoverable": total_recoverable,
        "prefix": PREFIX,
        "has_pdf_client": bool(session.pdf_client_path and os.path.exists(session.pdf_client_path or "")),
        "has_pdf_internal": bool(session.pdf_internal_path and os.path.exists(session.pdf_internal_path or "")),
    })


# ─── PDF download ─────────────────────────────────────────────────────────────

def _pdf_download_name(session, answers: dict) -> str:
    institution = answers.get("institution_name", "Institucion")
    safe = re.sub(r"[^\w\s-]", "", institution).strip()
    safe = re.sub(r"\s+", "_", safe) or "Institucion"
    ts = (session.analyzed_at or datetime.utcnow()).strftime("%Y_%m_%d_%H_%M")
    return f"Rayos_X_SuperLeads_{safe}_{ts}.pdf"


@app.get(PREFIX + "/pdf/cliente/{session_id}")
async def download_client_pdf(session_id: str, db: Session = Depends(get_db)):
    session = _get_session_or_404(session_id, db)
    if not session.pdf_client_path or not os.path.exists(session.pdf_client_path):
        raise HTTPException(status_code=404, detail="PDF no disponible")
    answers = session.get_answers()
    return FileResponse(
        session.pdf_client_path,
        media_type="application/pdf",
        filename=_pdf_download_name(session, answers)
    )


@app.get(PREFIX + "/pdf/interno/{session_id}")
async def download_internal_pdf(session_id: str, db: Session = Depends(get_db)):
    session = _get_session_or_404(session_id, db)
    if not session.pdf_internal_path or not os.path.exists(session.pdf_internal_path):
        raise HTTPException(status_code=404, detail="PDF no disponible")
    return FileResponse(
        session.pdf_internal_path,
        media_type="application/pdf",
        filename=f"RayosX_Interno_{session.short_code}.pdf"
    )


# ─── Método Comercial ─────────────────────────────────────────────────────────

@app.get("/Modelo_Comercial", response_class=HTMLResponse)
async def modelo_comercial():
    path = os.path.join(TEMPLATES_DIR, "rayosx", "modelo_comercial.html")
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/healthz")
async def health(db: Session = Depends(get_db)):
    """Health check completo: verifica DB + cuenta sesiones."""
    try:
        total     = db.execute(__import__("sqlalchemy").text("SELECT COUNT(*) FROM sessions")).scalar()
        analyzed  = db.execute(__import__("sqlalchemy").text("SELECT COUNT(*) FROM sessions WHERE status='analyzed'")).scalar()
        db_status = "ok"
    except Exception as e:
        return {"status": "degraded", "app": "Rayos X Inscripciones", "db": str(e)}, 503

    return {
        "status":   "ok",
        "app":      "Rayos X Inscripciones",
        "db":       db_status,
        "sessions": {"total": total, "analyzed": analyzed},
    }
