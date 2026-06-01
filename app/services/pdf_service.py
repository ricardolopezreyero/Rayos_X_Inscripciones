"""
PDF generation — Rayos X Inscripciones.

Narrative goal for the CLIENT pdf:
  The school director reads it and thinks:
  "This is exactly our problem. I didn't know it was this specific.
   I need to see what the solution looks like."

  No hard sell. No software pitch. Pure diagnostic clarity.
"""
from __future__ import annotations
import os, io, urllib.request
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY

# ── Palette ────────────────────────────────────────────────────────────────────
C_BG      = colors.HexColor("#05103a")
C_PANEL   = colors.HexColor("#0b1f69")
C_BLUE    = colors.HexColor("#2a89fb")
C_CYAN    = colors.HexColor("#1db2fc")
C_ACCENT  = colors.HexColor("#56ef9f")
C_TEXT    = colors.HexColor("#edf4ff")
C_MUTED   = colors.HexColor("#aac4ff")
C_WHITE   = colors.white
C_DARK    = colors.HexColor("#04102e")
C_RED     = colors.HexColor("#ff6b6b")
C_YELLOW  = colors.HexColor("#ffd93d")
C_PANEL2  = colors.HexColor("#081c5e")

W_PAGE    = 8.5 * inch          # letter width
MARGIN    = 0.72 * inch
W_CONTENT = W_PAGE - 2 * MARGIN  # usable width

PDF_DIR     = os.path.join(os.path.dirname(__file__), "../../static/pdfs")
ARCHIVO_DIR = os.path.join(os.path.dirname(__file__), "../../archivo")


def _archivo_path(session, answers: dict, tipo: str) -> str:
    """Devuelve la ruta de archivo permanente para un PDF.

    Estructura:  archivo/YYYY-MM/YYYY-MM-DD_CODIGO_Nombre-Institucion/cliente.pdf
    """
    inst = answers.get("institution_name", "Desconocida")
    safe = "".join(c if c.isalnum() or c in " -_" else "" for c in inst).strip()
    safe = safe.replace(" ", "-")[:40] or "Sin-Nombre"
    fecha = (getattr(session, "analyzed_at", None) or datetime.utcnow())
    mes   = fecha.strftime("%Y-%m")
    dia   = fecha.strftime("%Y-%m-%d")
    folder = os.path.join(ARCHIVO_DIR, mes, f"{dia}_{session.short_code}_{safe}")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{tipo}.pdf")


def _guardar_en_archivo(session, answers: dict, tipo: str, data: bytes) -> None:
    """Guarda una copia permanente del PDF en archivo/. Nunca falla silenciosamente."""
    try:
        dest = _archivo_path(session, answers, tipo)
        with open(dest, "wb") as fh:
            fh.write(data)
    except Exception as e:
        print(f"[archivo] Error guardando {tipo}: {e}")

LOGO_URL = "https://assets.cdn.filesafe.space/E6Gh1sE1RnPtadmL7wmG/media/69cffcaafa2dde9742fbf48b.png"
_LOGO_CACHE: dict = {}


def _get_logo():
    if "img" not in _LOGO_CACHE:
        try:
            from reportlab.lib.utils import ImageReader
            data = urllib.request.urlopen(LOGO_URL, timeout=5).read()
            _LOGO_CACHE["img"] = ImageReader(io.BytesIO(data))
        except Exception:
            _LOGO_CACHE["img"] = None
    return _LOGO_CACHE["img"]


def _ensure_dir():
    os.makedirs(PDF_DIR, exist_ok=True)


# ── Styles ─────────────────────────────────────────────────────────────────────
def S():
    return {
        "brand": ParagraphStyle("brand",
            fontName="Helvetica-Bold", fontSize=8.5,
            textColor=C_CYAN, spaceAfter=2, tracking=60),

        "institution": ParagraphStyle("institution",
            fontName="Helvetica-Bold", fontSize=20,
            textColor=C_WHITE, spaceAfter=4, leading=24),

        "tagline": ParagraphStyle("tagline",
            fontName="Helvetica", fontSize=11,
            textColor=C_MUTED, spaceAfter=3, leading=16),

        "section_title": ParagraphStyle("section_title",
            fontName="Helvetica-Bold", fontSize=13,
            textColor=C_ACCENT, spaceBefore=18, spaceAfter=8),

        "subsection": ParagraphStyle("subsection",
            fontName="Helvetica-Bold", fontSize=10.5,
            textColor=C_CYAN, spaceBefore=10, spaceAfter=5),

        "body": ParagraphStyle("body",
            fontName="Helvetica", fontSize=10,
            textColor=C_TEXT, spaceAfter=5, leading=16, alignment=TA_JUSTIFY),

        "body_bold": ParagraphStyle("body_bold",
            fontName="Helvetica-Bold", fontSize=10,
            textColor=C_TEXT, spaceAfter=4, leading=16),

        "muted": ParagraphStyle("muted",
            fontName="Helvetica", fontSize=9,
            textColor=C_MUTED, spaceAfter=3, leading=14),

        "small": ParagraphStyle("small",
            fontName="Helvetica", fontSize=8,
            textColor=C_MUTED, spaceAfter=2, leading=12),

        "finding_num": ParagraphStyle("finding_num",
            fontName="Helvetica-Bold", fontSize=22,
            textColor=colors.HexColor("#1a3580"), leading=24),

        "finding_title": ParagraphStyle("finding_title",
            fontName="Helvetica-Bold", fontSize=12,
            textColor=C_WHITE, spaceAfter=4, leading=16),

        "finding_body": ParagraphStyle("finding_body",
            fontName="Helvetica", fontSize=9.5,
            textColor=C_TEXT, spaceAfter=4, leading=15, alignment=TA_JUSTIFY),

        "finding_muted": ParagraphStyle("finding_muted",
            fontName="Helvetica", fontSize=8.5,
            textColor=C_MUTED, spaceAfter=3, leading=13),

        "impact_big": ParagraphStyle("impact_big",
            fontName="Helvetica-Bold", fontSize=19,
            textColor=C_ACCENT, spaceAfter=2, leading=22),

        "impact_label": ParagraphStyle("impact_label",
            fontName="Helvetica", fontSize=8.5,
            textColor=C_MUTED, spaceAfter=1),

        "callout": ParagraphStyle("callout",
            fontName="Helvetica-BoldOblique", fontSize=11,
            textColor=C_WHITE, leading=18, spaceAfter=6),

        "center_muted": ParagraphStyle("center_muted",
            fontName="Helvetica", fontSize=8.5,
            textColor=C_MUTED, alignment=TA_CENTER),

        "footer": ParagraphStyle("footer",
            fontName="Helvetica", fontSize=7.5,
            textColor=colors.HexColor("#3a5090"),
            alignment=TA_CENTER, leading=11),

        "sol_title": ParagraphStyle("sol_title",
            fontName="Helvetica-Bold", fontSize=10,
            textColor=C_WHITE, spaceAfter=3),

        "sol_body": ParagraphStyle("sol_body",
            fontName="Helvetica", fontSize=9,
            textColor=C_MUTED, leading=13, spaceAfter=2),

        "internal_warn": ParagraphStyle("internal_warn",
            fontName="Helvetica-Bold", fontSize=8,
            textColor=C_ACCENT, spaceAfter=8, tracking=40),
    }


# ── Helpers ────────────────────────────────────────────────────────────────────
def _bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(C_BG)
    canvas.rect(0, 0, letter[0], letter[1], fill=1, stroke=0)
    # top glow strip
    STRIP_H = 0.38 * inch
    canvas.setFillColor(colors.HexColor("#0a1e60"))
    canvas.rect(0, letter[1] - STRIP_H, letter[0], STRIP_H, fill=1, stroke=0)

    # logo icon
    logo_h = 0.24 * inch
    logo_y = letter[1] - STRIP_H + (STRIP_H - logo_h) / 2
    logo_img = _get_logo()
    if logo_img:
        canvas.drawImage(logo_img, MARGIN, logo_y, width=logo_h, height=logo_h, mask="auto")
        text_x = MARGIN + logo_h + 6
    else:
        text_x = MARGIN

    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(C_CYAN)
    canvas.drawString(text_x, logo_y + 6, "SUPERLEADS")
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#3a5090"))
    canvas.drawString(text_x, logo_y - 1, "Rayos X Inscripciones")

    # right: page info
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#2a4080"))
    canvas.drawRightString(letter[0] - MARGIN, logo_y + 3, "superleads.mx  ·  Sistema de Inscripciones Educativas")

    canvas.restoreState()


def _hr(color=C_BLUE, thickness=0.5, space_before=0, space_after=10):
    return HRFlowable(
        width="100%", thickness=thickness,
        color=color, spaceAfter=space_after, spaceBefore=space_before
    )


def _fmt(n, prefix="", suffix=""):
    if n is None:
        return "—"
    try:
        return f"{prefix}{int(n):,}{suffix}"
    except Exception:
        return str(n)


def _pct(n):
    if n is None:
        return "—"
    return f"{n*100:.1f}%"


def _severity_color(label):
    return {"Alta": C_ACCENT, "Media": C_CYAN, "Baja": C_MUTED}.get(label, C_BLUE)


def _conv_color(rate):
    """Color for a conversion rate."""
    if rate is None:
        return C_MUTED
    if rate >= 0.55:
        return C_ACCENT
    if rate >= 0.30:
        return C_YELLOW
    return C_RED


# ── Narrative builders ─────────────────────────────────────────────────────────
def _opening_paragraph(answers, metrics, s):
    """
    Personalized opening sentence that shows we understood their situation.
    Uses their actual numbers to make it concrete and credible.
    """
    institution = answers.get("institution_name", "su institución")
    leads       = metrics.get("leads")
    enrolled    = metrics.get("enrolled")
    enroll_rate = metrics.get("enroll_rate")
    target      = _parse_int(answers.get("target_new_enrollments"))
    gap         = metrics.get("gap_to_target")

    lines = []

    if enroll_rate is not None and leads is not None and enrolled is not None:
        per_100 = int(enroll_rate * 100)
        lost    = leads - enrolled
        lines.append(
            f"De cada 100 prospectos que entran al sistema de <b>{institution}</b>, "
            f"solo <b>{per_100} llegan a inscribirse</b>. "
            f"Eso significa que en el período analizado, "
            f"<b>{_fmt(lost)} prospectos</b> no se convirtieron en alumnos."
        )
    elif leads is not None:
        lines.append(
            f"Con <b>{_fmt(leads)} prospectos</b> registrados, "
            f"<b>{institution}</b> tiene la materia prima para crecer."
        )
    elif enrolled is not None:
        lines.append(
            f"El análisis de <b>{institution}</b> revela patrones claros "
            f"en el sistema de admisiones que explicaremos a continuación."
        )

    if gap and gap > 0:
        lines.append(
            f"La brecha hacia la meta es de <b>{_fmt(gap)} alumnos</b>. "
            f"El diagnóstico que sigue identifica exactamente qué está bloqueando ese crecimiento."
        )

    if not lines:
        lines.append(
            f"El siguiente diagnóstico analiza el sistema de inscripciones de "
            f"<b>{institution}</b> para identificar los principales cuellos de botella."
        )

    return Paragraph(" ".join(lines), s["body"])


def _opportunity_narrative(answers, metrics, s):
    """Show the economic cost of the problem — the 'burning money' section."""
    items = []
    ticket  = _parse_int(answers.get("average_ticket"))
    opp_val = metrics.get("opportunity_value")
    gap     = metrics.get("gap_to_target")
    cap     = metrics.get("capacity_available")
    leads   = metrics.get("leads")
    enrolled = metrics.get("enrolled")
    enroll_rate = metrics.get("enroll_rate")

    if not (opp_val or gap):
        return items

    items.append(Paragraph("El tamaño de la oportunidad", s["section_title"]))

    # Narrative sentence
    if gap and ticket:
        annual = gap * ticket
        items.append(Paragraph(
            f"Si se lograra la meta de inscritos y cada alumno paga en promedio "
            f"<b>${ticket:,}</b> al año, existe una oportunidad de "
            f"<b>${annual:,.0f}</b> en ingresos adicionales — "
            f"sin necesidad de ampliar instalaciones ni contratar más docentes.",
            s["body"]
        ))
    elif opp_val:
        items.append(Paragraph(
            f"Con el cupo disponible y el ticket actual, la institución tiene una "
            f"oportunidad de hasta <b>${opp_val:,.0f}</b> en ingresos anuales adicionales "
            f"si mejora la conversión de su sistema actual.",
            s["body"]
        ))

    # Metric boxes
    box_data = []
    if gap:
        box_data.append((f"{gap:,}", "alumnos\nde brecha"))
    if ticket:
        box_data.append((f"${ticket:,}", "colegiatura\npromedio/año"))
    if opp_val:
        box_data.append((f"${opp_val:,.0f}", "oportunidad\nestimada"))

    if box_data:
        items.append(Spacer(1, 6))
        cells = []
        for val_text, lbl_text in box_data:
            cell = [
                Paragraph(val_text, s["impact_big"]),
                Paragraph(lbl_text, s["impact_label"]),
            ]
            cells.append(cell)

        col_w = W_CONTENT / max(len(box_data), 1)
        t = Table([cells], colWidths=[col_w]*len(box_data))
        t.setStyle(TableStyle([
            ("BACKGROUND",   (0,0),(-1,-1), C_PANEL2),
            ("GRID",         (0,0),(-1,-1), 0.5, colors.HexColor("#0f2b7a")),
            ("TOPPADDING",   (0,0),(-1,-1), 14),
            ("BOTTOMPADDING",(0,0),(-1,-1), 14),
            ("LEFTPADDING",  (0,0),(-1,-1), 16),
            ("RIGHTPADDING", (0,0),(-1,-1), 16),
            ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
            ("ROUNDEDCORNERS",(0,0),(-1,-1), 6),
        ]))
        items.append(t)
        items.append(Spacer(1, 8))

    items.append(Paragraph(
        "Nota: esta estimación se basa en el cupo disponible y el ticket reportado. "
        "El diagnóstico no hace promesas de resultado — muestra el potencial si se corrige el sistema.",
        s["small"]
    ))

    return items


def _funnel_table(metrics, s):
    """Visual funnel table with loss numbers and conversion colors."""
    stages = [
        ("Leads",           "leads"),
        ("Contactados",     "contacted"),
        ("Citas agendadas", "appointments"),
        ("Asistentes",      "attended"),
        ("Inscritos",       "enrolled"),
    ]
    conv_keys = {
        "contacted":    ("contact_rate",            "Contactación"),
        "appointments": ("appointment_rate_leads",  "Conv. a cita"),
        "attended":     ("attendance_rate",         "Asistencia"),
        "enrolled":     ("close_rate_attended",     "Cierre"),
    }

    rows = [["Etapa", "Valor", "Conversión", "Pérdida absoluta"]]
    has_data = False

    prev_val = None
    for label, key in stages:
        val = metrics.get(key)
        if val is None:
            continue
        has_data = True
        val_int = int(val)

        ck, _ = conv_keys.get(key, (None, None))
        if ck:
            rate = metrics.get(ck)
            conv_str  = _pct(rate) if rate is not None else "—"
            conv_color = _conv_color(rate) if rate is not None else C_MUTED
        else:
            conv_str  = "—"
            conv_color = C_MUTED

        loss_str  = ""
        loss_color = C_MUTED
        if prev_val is not None:
            loss = prev_val - val_int
            if loss > 0:
                loss_str  = f"−{loss:,}"
                loss_color = C_RED if loss / max(prev_val,1) > 0.5 else C_YELLOW

        rows.append([
            Paragraph(label, s["finding_body"]),
            Paragraph(f"<b>{val_int:,}</b>", s["finding_body"]),
            Paragraph(f"<b>{conv_str}</b>",
                ParagraphStyle("cv", fontName="Helvetica-Bold", fontSize=9.5,
                               textColor=conv_color, leading=14)),
            Paragraph(loss_str,
                ParagraphStyle("ls", fontName="Helvetica-Bold", fontSize=9.5,
                               textColor=loss_color, leading=14)),
        ])
        prev_val = val_int

    if not has_data or len(rows) <= 1:
        return []

    col_widths = [W_CONTENT*0.35, W_CONTENT*0.18, W_CONTENT*0.25, W_CONTENT*0.22]
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        # Header
        ("BACKGROUND",    (0,0),(-1,0), C_PANEL),
        ("TEXTCOLOR",     (0,0),(-1,0), C_CYAN),
        ("FONTNAME",      (0,0),(-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,0), 8.5),
        # Data rows — alternating
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [C_BG, colors.HexColor("#070d2d")]),
        ("GRID",          (0,0),(-1,-1), 0.4, colors.HexColor("#0d2070")),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("ALIGN",         (1,0),(-1,-1), "CENTER"),
    ]))
    return [t]


def _journey_steps_pdf(s):
    """Diagnóstico ✓ → Diseño Solución → Implementación → Optimización bar."""
    steps = [
        ("✓", "Diagnóstico",       True),
        ("2", "Diseño Solución",   False),
        ("3", "Implementación",    False),
        ("4", "Optimización",      False),
    ]
    cells = []
    for num, name, done in steps:
        num_color  = C_ACCENT if done else C_MUTED
        name_color = C_TEXT   if done else colors.HexColor("#3a5090")
        cells.append([
            Paragraph(f"<b>{num}</b>", ParagraphStyle("jn", fontName="Helvetica-Bold",
                       fontSize=14, textColor=num_color, alignment=TA_CENTER, leading=16)),
            Paragraph(name, ParagraphStyle("jl", fontName="Helvetica-Bold" if done else "Helvetica",
                       fontSize=8, textColor=name_color, alignment=TA_CENTER, leading=11)),
        ])
    cw = W_CONTENT / len(steps)
    t = Table([cells], colWidths=[cw]*len(steps))
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,0),  colors.HexColor("#061a0a")),
        ("BACKGROUND",    (1,0), (-1,0), C_PANEL2),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#0c1f50")),
        ("LINEABOVE",     (0,0), (0,0),  2, C_ACCENT),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
    ]))
    return [t, Spacer(1, 8)]


def _solutions_block_client(f, s):
    """Solutions section for the CLIENT pdf — visual cards with colored left stripe."""
    solutions = f.get("solutions", [])
    if not solutions:
        return []

    items = []
    sol_header = Table(
        [[Paragraph("  CÓMO LO RESUELVE SUPERLEADS", ParagraphStyle("sh",
            fontName="Helvetica-Bold", fontSize=8, textColor=C_CYAN,
            spaceAfter=0, tracking=40))]],
        colWidths=[W_CONTENT]
    )
    sol_header.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), colors.HexColor("#051830")),
        ("TOPPADDING",   (0,0),(-1,-1), 7),
        ("BOTTOMPADDING",(0,0),(-1,-1), 7),
        ("LEFTPADDING",  (0,0),(-1,-1), 14),
        ("LINEABOVE",    (0,0),(-1,0),  1.5, C_CYAN),
    ]))
    items.append(sol_header)

    STRIPE = 5  # left accent stripe width in points
    role_color = {
        "primary":       C_ACCENT,
        "complementary": C_CYAN,
        "prerequisite":  C_YELLOW,
    }
    role_label = {
        "primary":       "SOLUCIÓN PRINCIPAL",
        "complementary": "COMPLEMENTARIA",
        "prerequisite":  "BASE NECESARIA",
    }

    for sol in solutions:
        role    = sol.get("role", "primary")
        accent  = role_color.get(role, C_BLUE)
        badge   = role_label.get(role, "HERRAMIENTA")
        name    = sol.get("name", "")
        msg     = sol.get("public_message", "")

        content_cell = [
            Paragraph(badge, ParagraphStyle("slbl", fontName="Helvetica-Bold",
                fontSize=6.5, textColor=accent, leading=9, tracking=50, spaceAfter=3)),
            Paragraph(f"<b>{name}</b>", ParagraphStyle("snm", fontName="Helvetica-Bold",
                fontSize=10.5, textColor=C_WHITE, leading=14, spaceAfter=5)),
            Paragraph(msg, ParagraphStyle("smsg", fontName="Helvetica", fontSize=9,
                textColor=C_TEXT, leading=13.5, alignment=TA_JUSTIFY)),
        ]
        card = Table([[ "", content_cell ]], colWidths=[STRIPE, W_CONTENT - STRIPE])
        card.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (0,0),  accent),
            ("BACKGROUND",    (1,0), (1,0),  colors.HexColor("#06122e")),
            ("LINEBELOW",     (0,0), (-1,-1), 0.4, colors.HexColor("#0c1f60")),
            ("TOPPADDING",    (0,0), (0,0),  0),
            ("BOTTOMPADDING", (0,0), (0,0),  0),
            ("LEFTPADDING",   (0,0), (0,0),  0),
            ("RIGHTPADDING",  (0,0), (0,0),  0),
            ("TOPPADDING",    (1,0), (1,0),  10),
            ("BOTTOMPADDING", (1,0), (1,0),  10),
            ("LEFTPADDING",   (1,0), (1,0),  12),
            ("RIGHTPADDING",  (1,0), (1,0),  12),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ]))
        items.append(card)

    items.append(Spacer(1, 6))
    return items


def _finding_block_client(f, idx, s):
    """
    One finding for the CLIENT pdf.
    Narrative: what's happening → why it matters → what it costs.
    Includes public-facing solutions.
    """
    sev_color = _severity_color(f.get("severity_label","Media"))
    items     = []

    # ── Header ──
    header_cells = [[
        [Paragraph(f"#{idx}", s["finding_num"]),
         Paragraph(f.get("title",""), s["finding_title"])],
        [Paragraph(f"Severidad: <b>{f.get('severity_label','—')}</b>",  s["finding_muted"]),
         Paragraph(f"Certeza:    <b>{f.get('confidence_label','—')}</b>", s["finding_muted"]),
         Paragraph(f"Zona:       <b>{f.get('funnel_zone','—')}</b>",      s["finding_muted"])],
    ]]
    ht = Table(header_cells, colWidths=[W_CONTENT*0.62, W_CONTENT*0.38])
    ht.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_PANEL),
        ("LEFTPADDING",   (0,0),(-1,-1), 14),
        ("RIGHTPADDING",  (0,0),(-1,-1), 14),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LINEABOVE",     (0,0),(-1,0),  3, sev_color),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
    ]))
    items.append(KeepTogether([ht]))

    # ── Body ──
    body_rows = [
        [Paragraph("<b>Lo que encontramos</b>", s["finding_muted"]),
         Paragraph(f.get("summary",""), s["finding_body"])],
        [Paragraph("<b>Por qué ocurre</b>", s["finding_muted"]),
         Paragraph(f.get("rationale",""), s["finding_body"])],
    ]
    if f.get("estimated_impact"):
        body_rows.append([
            Paragraph("<b>Impacto estimado</b>", s["finding_muted"]),
            Paragraph(f"<b>{f['estimated_impact']}</b>",
                ParagraphStyle("imp", fontName="Helvetica-Bold", fontSize=9.5,
                               textColor=C_ACCENT, leading=14)),
        ])
    if f.get("missing_data"):
        body_rows.append([
            Paragraph("<b>Para mayor certeza</b>", s["finding_muted"]),
            Paragraph(f.get("missing_data",""), s["finding_muted"]),
        ])
    if f.get("evidence"):
        ev_text = "  ·  ".join(f["evidence"])
        body_rows.append([
            Paragraph("<b>Evidencia usada</b>", s["finding_muted"]),
            Paragraph(ev_text, s["finding_muted"]),
        ])

    bt = Table(body_rows, colWidths=[W_CONTENT*0.25, W_CONTENT*0.75])
    bt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#060d2a")),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
        ("RIGHTPADDING",  (0,0),(-1,-1), 12),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LINEBELOW",     (0,0),(-1,-2), 0.3, colors.HexColor("#0c1f60")),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
    ]))
    items.append(bt)
    items.extend(_solutions_block_client(f, s))
    items.append(Spacer(1, 12))
    return items


def _finding_block_internal(f, idx, s):
    """Finding + solutions for the INTERNAL pdf."""
    items = _finding_block_client(f, idx, s)

    solutions = f.get("solutions", [])
    if not solutions:
        return items

    role_map = {"primary": "Principal", "complementary": "Complementaria",
                "prerequisite": "Precondición", "external": "Externo"}

    sol_header = Table(
        [[Paragraph("  SOLUCIONES SUPERLEADS", s["internal_warn"])]],
        colWidths=[W_CONTENT]
    )
    sol_header.setStyle(TableStyle([
        ("BACKGROUND",  (0,0),(-1,-1), colors.HexColor("#0a1e52")),
        ("TOPPADDING",  (0,0),(-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING", (0,0),(-1,-1), 12),
    ]))
    items.append(sol_header)

    for sol in solutions:
        role_label = role_map.get(sol.get("role",""), sol.get("role",""))
        sol_rows = [
            [Paragraph(f"<b>{sol.get('name','')}</b>   [{role_label}]", s["sol_title"]),
             Paragraph(sol.get("internal_message",""), s["sol_body"])],
            [Paragraph(sol.get("public_message",""), s["sol_body"]),
             Paragraph(f"🎯 {sol.get('demo_angle','')}", s["sol_body"])],
        ]
        st = Table(sol_rows, colWidths=[W_CONTENT*0.48, W_CONTENT*0.52])
        st.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#06122e")),
            ("LINEBELOW",     (0,0),(-1,-2), 0.3, colors.HexColor("#0c1f60")),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 12),
            ("RIGHTPADDING",  (0,0),(-1,-1), 12),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ]))
        items.append(st)

    items.append(Spacer(1, 14))
    return items


def _comparison_funnel_pdf(metrics, answers, s):
    """
    Side-by-side flow: Sin sistema vs. Con SuperLeads.
    Uses the actual funnel data on the left and SuperLeads benchmarks on the right.
    """
    leads    = _parse_int(metrics.get("leads"))
    enrolled = _parse_int(metrics.get("enrolled"))
    if not leads or not enrolled:
        return []

    # Current values (estimate middle stages if missing)
    contacted    = _parse_int(metrics.get("contacted"))    or int(leads * 0.45)
    appointments = _parse_int(metrics.get("appointments")) or int(contacted * 0.35)
    attended     = _parse_int(metrics.get("attended"))     or int(appointments * 0.70)

    # Projected "Con SuperLeads" — conservative benchmarks (–20% margin)
    p_contacted    = int(leads * 0.65)
    p_appointments = int(p_contacted * 0.45)
    p_attended     = int(p_appointments * 0.68)
    p_enrolled     = int(p_attended * 0.55)
    gain           = p_enrolled - enrolled

    ticket = _parse_int(answers.get("average_ticket"))

    items = []
    items.append(Paragraph("El mismo prospecto — distinto destino", s["section_title"]))
    items.append(Paragraph(
        "Cómo cambia el flujo de inscripciones con un sistema bien instalado. "
        "Los leads son los mismos — lo que cambia es qué le pasa a cada uno.",
        s["muted"]
    ))
    items.append(Spacer(1, 10))

    # ── Table structure ───────────────────────────────────────────────────────
    W_SIDE = W_CONTENT * 0.42
    W_MID  = W_CONTENT * 0.16
    COL_W  = [W_SIDE, W_MID, W_SIDE]

    def _stage_cell(label, value, val_color, bg_color, border_color):
        """Returns a [label_para, value_para] list for a stage cell."""
        return [
            Paragraph(label, ParagraphStyle("fl", fontName="Helvetica", fontSize=7.5,
                                            textColor=C_MUTED, alignment=TA_CENTER)),
            Paragraph(f"<b>{value:,}</b>", ParagraphStyle("fv", fontName="Helvetica-Bold",
                                            fontSize=13, textColor=val_color,
                                            alignment=TA_CENTER, leading=16)),
        ]

    def _conv_color_str(rate):
        if rate >= 0.60: return C_ACCENT
        if rate >= 0.35: return C_YELLOW
        return C_RED

    # Conversion rates — current
    r1 = contacted    / leads       if leads       else 0
    r2 = appointments / contacted   if contacted   else 0
    r3 = attended     / appointments if appointments else 0
    r4 = enrolled     / attended    if attended    else 0

    stages = [
        ("Leads",       leads,       enrolled,    C_TEXT,   C_TEXT),
        ("Contactados", contacted,   p_contacted,   _conv_color_str(r1), C_ACCENT),
        ("Citas",       appointments, p_appointments, _conv_color_str(r2), C_ACCENT),
        ("Asistentes",  attended,    p_attended,  _conv_color_str(r3), C_ACCENT),
        ("Inscritos",   enrolled,    p_enrolled,  C_RED,    C_ACCENT),
    ]
    cur_rates  = [None, r1, r2, r3, r4]
    proj_rates = [None, 0.65, 0.45, 0.68, 0.55]

    # Header row
    def _col_header(text, color):
        return Paragraph(f"<b>{text}</b>", ParagraphStyle("ch", fontName="Helvetica-Bold",
                         fontSize=8, textColor=color, alignment=TA_CENTER))

    table_rows = []
    row_styles = []

    # Column headers
    table_rows.append([
        _col_header("Sin sistema", C_RED),
        Paragraph("", s["small"]),
        _col_header("Con SuperLeads", C_ACCENT),
    ])
    row_styles.append(("BACKGROUND", (0,0), (0,0), colors.HexColor("#1a0606")))
    row_styles.append(("BACKGROUND", (2,0), (2,0), colors.HexColor("#061a06")))
    row_styles.append(("TOPPADDING",    (0,0), (-1,0), 6))
    row_styles.append(("BOTTOMPADDING", (0,0), (-1,0), 6))

    for idx, (stage_name, cur_val, proj_val, cur_color, proj_color) in enumerate(stages):
        row_n = len(table_rows)

        # Stage row
        left_cell  = [
            Paragraph(stage_name, ParagraphStyle("sn", fontName="Helvetica", fontSize=7.5,
                                                  textColor=C_MUTED, alignment=TA_CENTER)),
            Paragraph(f"<b>{cur_val:,}</b>", ParagraphStyle("sv", fontName="Helvetica-Bold",
                                              fontSize=14, textColor=cur_color,
                                              alignment=TA_CENTER, leading=17)),
        ]
        right_cell = [
            Paragraph(stage_name, ParagraphStyle("sn2", fontName="Helvetica", fontSize=7.5,
                                                  textColor=C_MUTED, alignment=TA_CENTER)),
            Paragraph(f"<b>{proj_val:,}</b>", ParagraphStyle("sv2", fontName="Helvetica-Bold",
                                               fontSize=14, textColor=proj_color,
                                               alignment=TA_CENTER, leading=17)),
        ]
        arrow_text = "→" if idx == 2 else ""
        mid_cell   = Paragraph(arrow_text, ParagraphStyle("ar", fontName="Helvetica-Bold",
                                fontSize=16, textColor=C_ACCENT, alignment=TA_CENTER))

        table_rows.append([left_cell, mid_cell, right_cell])

        left_bg  = colors.HexColor("#120606") if idx == 4 else colors.HexColor("#0a0d1e")
        right_bg = colors.HexColor("#061206") if idx == 4 else colors.HexColor("#060d12")
        row_styles.append(("BACKGROUND",    (0, row_n), (0, row_n), left_bg))
        row_styles.append(("BACKGROUND",    (2, row_n), (2, row_n), right_bg))
        row_styles.append(("BACKGROUND",    (1, row_n), (1, row_n), C_BG))
        row_styles.append(("TOPPADDING",    (0, row_n), (-1, row_n), 8))
        row_styles.append(("BOTTOMPADDING", (0, row_n), (-1, row_n), 8))

        if idx == 4:
            row_styles.append(("LINEABOVE", (0, row_n), (0, row_n), 1.5, colors.HexColor("#662222")))
            row_styles.append(("LINEABOVE", (2, row_n), (2, row_n), 1.5, C_ACCENT))

        # Conversion row (not after last)
        if idx < 4:
            conv_row_n = len(table_rows)
            cr_cur  = cur_rates[idx + 1]
            cr_proj = proj_rates[idx + 1]
            cur_rate_color  = _conv_color_str(cr_cur)
            proj_rate_color = C_ACCENT

            table_rows.append([
                Paragraph(f"↓ {cr_cur*100:.0f}%", ParagraphStyle("cr", fontName="Helvetica-Bold",
                          fontSize=9, textColor=cur_rate_color, alignment=TA_CENTER)),
                Paragraph("", s["small"]),
                Paragraph(f"↓ {cr_proj*100:.0f}%", ParagraphStyle("cr2", fontName="Helvetica-Bold",
                          fontSize=9, textColor=proj_rate_color, alignment=TA_CENTER)),
            ])
            row_styles.append(("BACKGROUND",    (0, conv_row_n), (0, conv_row_n), C_BG))
            row_styles.append(("BACKGROUND",    (1, conv_row_n), (1, conv_row_n), C_BG))
            row_styles.append(("BACKGROUND",    (2, conv_row_n), (2, conv_row_n), C_BG))
            row_styles.append(("TOPPADDING",    (0, conv_row_n), (-1, conv_row_n), 2))
            row_styles.append(("BOTTOMPADDING", (0, conv_row_n), (-1, conv_row_n), 2))

    t = Table(table_rows, colWidths=COL_W)
    base_style = [
        ("GRID",         (0,0), (-1,-1), 0.3, colors.HexColor("#0c1f50")),
        ("LEFTPADDING",  (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN",        (0,0), (-1,-1), "CENTER"),
        ("NOSPLIT",      (0,0), (-1,-1)),
    ]
    t.setStyle(TableStyle(base_style + row_styles))
    items.append(t)
    items.append(Spacer(1, 8))

    # Gain summary
    if gain > 0:
        gain_parts = [f"Diferencia potencial: <b>+{gain:,} alumnos adicionales por ciclo</b>"]
        if ticket and ticket > 0:
            gain_parts.append(f"— equivalente a <b>${gain * ticket:,.0f}</b> adicionales/año")
        items.append(Paragraph(
            "  ".join(gain_parts),
            ParagraphStyle("gain", fontName="Helvetica-Bold", fontSize=10,
                           textColor=C_ACCENT, alignment=TA_CENTER,
                           backColor=colors.HexColor("#061a0a"),
                           borderPad=8, spaceAfter=4,
                           leftIndent=0, rightIndent=0, leading=16)
        ))
        items.append(Spacer(1, 4))

    items.append(Paragraph(
        "* Proyección conservadora SuperLeads: contactación 65%, citas 45%, asistencia 68%, cierre 55%. "
        "Margen incorporado para entregar más de lo que se proyecta. Resultados reales dependen de implementación.",
        s["small"]
    ))
    items.append(Spacer(1, 6))
    return items


CALENDAR_URL = "https://link.superleads.mx/widget/bookings/superleads_revision_diagnostico_propuesta_comercial"


def _strategic_direction_block(s):
    """Always-present Dirección Estratégica SuperLeads recommendation card."""
    items = []

    header = Table([[
        Paragraph("★  DIRECCIÓN ESTRATÉGICA SUPERLEADS", ParagraphStyle("deh",
            fontName="Helvetica-Bold", fontSize=9, textColor=C_ACCENT,
            spaceAfter=0, tracking=40))
    ]], colWidths=[W_CONTENT])
    header.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#061a0a")),
        ("TOPPADDING",    (0,0),(-1,-1), 11),
        ("BOTTOMPADDING", (0,0),(-1,-1), 11),
        ("LEFTPADDING",   (0,0),(-1,-1), 16),
        ("LINEABOVE",     (0,0),(-1,0),  2.5, C_ACCENT),
        ("LINEBELOW",     (0,0),(-1,-1), 0.5, colors.HexColor("#0f4020")),
    ]))
    items.append(header)

    intro = Table([[
        Paragraph(
            "Un diagnóstico sin sistema de ejecución sólo produce buenas intenciones. "
            "Dirección Estratégica es el acompañamiento continuo que convierte estos hallazgos "
            "en resultados medibles cada ciclo.",
            ParagraphStyle("dei", fontName="Helvetica-Oblique", fontSize=9,
                textColor=C_MUTED, leading=13.5, alignment=TA_JUSTIFY)
        )
    ]], colWidths=[W_CONTENT])
    intro.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#060f1a")),
        ("TOPPADDING",    (0,0),(-1,-1), 9),
        ("BOTTOMPADDING", (0,0),(-1,-1), 9),
        ("LEFTPADDING",   (0,0),(-1,-1), 16),
        ("RIGHTPADDING",  (0,0),(-1,-1), 16),
        ("LINEBELOW",     (0,0),(-1,-1), 0.4, colors.HexColor("#0f4020")),
    ]))
    items.append(intro)

    STRIPE = 5
    bullets = [
        ("Sistema completo, no piezas sueltas",
         "SuperLeads diseña, instala y opera todo el Sistema de Inscripciones: CRM, "
         "procesos, formación del equipo y métricas, en un solo contrato sin intermediarios."),
        ("Estrategia + ejecución continua",
         "Acompañamiento permanente del asesor para ajustar la estrategia según los "
         "resultados reales de cada ciclo. No te deja solo después de la instalación."),
        ("Decisiones con datos, no intuición",
         "Métricas del embudo en tiempo real — contactación, citas, asistencia y cierre — "
         "para saber exactamente qué palanca mover en cada momento."),
        ("Resultados medibles por ciclo",
         "Compromisos claros de seguimiento: si los indicadores no avanzan, "
         "la estrategia se ajusta. El objetivo es que los números mejoren, no sólo que se midan."),
    ]

    for title, desc in bullets:
        row = Table([[
            "",
            [
                Paragraph(f"<b>{title}</b>", ParagraphStyle("bt", fontName="Helvetica-Bold",
                    fontSize=9, textColor=C_ACCENT, leading=13, spaceAfter=3)),
                Paragraph(desc, ParagraphStyle("bd", fontName="Helvetica", fontSize=9,
                    textColor=C_TEXT, leading=13, alignment=TA_JUSTIFY)),
            ],
        ]], colWidths=[STRIPE, W_CONTENT - STRIPE])
        row.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (0,0),  C_ACCENT),
            ("BACKGROUND",    (1,0), (1,0),  colors.HexColor("#060f1e")),
            ("LINEBELOW",     (0,0), (-1,-1), 0.4, colors.HexColor("#0f4020")),
            ("TOPPADDING",    (0,0), (0,0),  0),
            ("BOTTOMPADDING", (0,0), (0,0),  0),
            ("LEFTPADDING",   (0,0), (0,0),  0),
            ("RIGHTPADDING",  (0,0), (0,0),  0),
            ("TOPPADDING",    (1,0), (1,0),  9),
            ("BOTTOMPADDING", (1,0), (1,0),  9),
            ("LEFTPADDING",   (1,0), (1,0),  14),
            ("RIGHTPADDING",  (1,0), (1,0),  14),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ]))
        items.append(row)

    items.append(Spacer(1, 12))
    return items


def _closing_block(s, is_preliminary=False):
    items = []
    items.append(_hr(C_BLUE, space_before=6))

    # Journey steps
    items.extend(_journey_steps_pdf(s))

    items.append(Paragraph("Próximo paso: Diseño de Solución", s["section_title"]))

    if is_preliminary:
        msg = (
            "Este es un diagnóstico preliminar basado en los datos disponibles. "
            "Tiene suficiente claridad para arrancar una conversación productiva, "
            "pero se fortalece con más datos del embudo completo. "
            "La siguiente reunión es para revisar qué sistema resuelve exactamente lo que se detectó."
        )
    else:
        msg = (
            "El diagnóstico está completo y los hallazgos son concretos. "
            "La siguiente conversación no es una propuesta comercial genérica — "
            "es diseñar exactamente qué intervención resuelve cada cuello detectado, "
            "en el orden de prioridad que el propio sistema reveló."
        )

    items.append(Paragraph(msg, s["body"]))
    items.append(Spacer(1, 10))

    # CTA box
    cta_table = Table([[
        Paragraph(
            f"Agenda tu Diseño de Solución:<br/>"
            f"<b><font color='#56ef9f'>{CALENDAR_URL}</font></b>",
            ParagraphStyle("cta_url", fontName="Helvetica", fontSize=10,
                           textColor=C_TEXT, leading=16, alignment=TA_CENTER)
        )
    ]], colWidths=[W_CONTENT])
    cta_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#061a0a")),
        ("TOPPADDING",    (0,0),(-1,-1), 16),
        ("BOTTOMPADDING", (0,0),(-1,-1), 16),
        ("LEFTPADDING",   (0,0),(-1,-1), 20),
        ("RIGHTPADDING",  (0,0),(-1,-1), 20),
        ("LINEABOVE",     (0,0),(-1,0),  2, C_ACCENT),
        ("LINEBELOW",     (0,0),(-1,-1), 2, C_ACCENT),
    ]))
    items.append(cta_table)
    items.append(Spacer(1, 8))
    items.append(Paragraph(
        "<i>SuperLeads no vende piezas sueltas. Diseña y opera el Sistema de Inscripciones completo.</i>",
        s["callout"]
    ))
    return items


# ── Main PDF generators ────────────────────────────────────────────────────────
def generate_client_pdf(session, answers: dict, result: dict) -> str:
    _ensure_dir()
    filename = f"rayosx_cliente_{session.short_code}.pdf"
    filepath = os.path.join(PDF_DIR, filename)
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=0.65*inch, bottomMargin=0.65*inch,
        title=f"Rayos X — {answers.get('institution_name','')}"
    )

    s = S()
    story = []
    metrics        = result.get("metrics", {})
    findings       = result.get("findings", [])
    completeness   = result.get("completeness_score", 0)
    certainty      = result.get("certainty_score", 0)
    is_preliminary = result.get("is_preliminary", False)
    institution    = answers.get("institution_name", "Institución")
    contact        = answers.get("contact_name", "")
    city           = answers.get("city", "")

    # ── Cover / header ─────────────────────────────────────────────────────
    story.extend(_journey_steps_pdf(s))
    story.append(Paragraph("RAYOS X INSCRIPCIONES  ·  SUPERLEADS", s["brand"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(institution, s["institution"]))

    meta_parts = [f"Contacto: {contact}" if contact else "",
                  city,
                  f"Sesión {session.short_code}",
                  datetime.now().strftime("%d/%m/%Y")]
    story.append(Paragraph("  ·  ".join(p for p in meta_parts if p), s["tagline"]))
    story.append(Spacer(1, 4))

    # Score row
    scores = [
        (f"{completeness:.0f}%", "Completitud\nde datos"),
        (f"{certainty:.0f}%",    "Certeza del\ndiagnóstico"),
    ]
    if metrics.get("opportunity_value"):
        scores.append((f"${metrics['opportunity_value']:,.0f}", "Oportunidad\nestimada"))
    if metrics.get("gap_to_target") and int(metrics["gap_to_target"]) > 0:
        scores.append((f"{int(metrics['gap_to_target']):,}", "Alumnos\nde brecha"))

    score_cells = [[
        [Paragraph(v, s["impact_big"]),
         Paragraph(l, s["impact_label"])]
        for v, l in scores
    ]]
    cw = W_CONTENT / len(scores)
    st = Table(score_cells, colWidths=[cw]*len(scores))
    st.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_PANEL),
        ("GRID",          (0,0),(-1,-1), 0.4, colors.HexColor("#0d2070")),
        ("TOPPADDING",    (0,0),(-1,-1), 12),
        ("BOTTOMPADDING", (0,0),(-1,-1), 12),
        ("LEFTPADDING",   (0,0),(-1,-1), 14),
        ("RIGHTPADDING",  (0,0),(-1,-1), 14),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(st)
    story.append(Spacer(1, 10))
    story.append(_hr())

    # ── Opening ────────────────────────────────────────────────────────────
    story.append(Paragraph("Lo que encontramos", s["section_title"]))
    story.append(_opening_paragraph(answers, metrics, s))
    story.append(Spacer(1, 6))

    if is_preliminary:
        story.append(Paragraph(
            "⚠  Diagnóstico preliminar — datos suficientes para identificar el patrón principal, "
            "pero con certeza reducida. Más datos del embudo elevarían la confianza.",
            ParagraphStyle("warn", fontName="Helvetica-BoldOblique", fontSize=9,
                           textColor=C_YELLOW, leading=14, spaceAfter=6,
                           backColor=colors.HexColor("#1a1200"),
                           leftIndent=8, rightIndent=8,
                           borderPad=6)
        ))

    # ── Funnel table ───────────────────────────────────────────────────────
    funnel_rows = _funnel_table(metrics, s)
    if funnel_rows:
        story.append(Paragraph("El embudo, con sus fugas", s["section_title"]))
        story.append(Paragraph(
            "La columna 'Pérdida absoluta' muestra cuántos prospectos desaparecen en cada transición. "
            "El color indica si esa conversión está en zona crítica (rojo), de atención (amarillo) o saludable (verde).",
            s["muted"]
        ))
        story.append(Spacer(1, 6))
        story.extend(funnel_rows)
        story.append(Spacer(1, 8))

    # ── Comparison funnel ──────────────────────────────────────────────────
    comp_items = _comparison_funnel_pdf(metrics, answers, s)
    if comp_items:
        story.extend(comp_items)
        story.append(Spacer(1, 4))

    # ── Opportunity ────────────────────────────────────────────────────────
    opp_items = _opportunity_narrative(answers, metrics, s)
    if opp_items:
        story.extend(opp_items)
        story.append(Spacer(1, 4))

    # ── Findings ───────────────────────────────────────────────────────────
    if findings:
        story.append(Paragraph(
            f"{'Hallazgos principales' if not is_preliminary else 'Hallazgos preliminares'} "
            f"({len(findings)} detectado{'s' if len(findings) != 1 else ''})",
            s["section_title"]
        ))
        story.append(Paragraph(
            "Ordenados por prioridad: el primero es el cuello que más impacto tiene en el crecimiento hoy.",
            s["muted"]
        ))
        story.append(Spacer(1, 6))
        for i, f in enumerate(findings, 1):
            story.extend(_finding_block_client(f, i, s))

    # ── Dirección Estratégica (always present) ─────────────────────────────
    story.append(Paragraph("La recomendación del sistema", s["section_title"]))
    story.extend(_strategic_direction_block(s))

    # ── Closing ────────────────────────────────────────────────────────────
    story.extend(_closing_block(s, is_preliminary))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        f"superleads.mx  ·  Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}  ·  "
        f"Sesión {session.short_code}  ·  Este reporte es confidencial.",
        s["footer"]
    ))

    doc.build(story, onFirstPage=_bg, onLaterPages=_bg)
    pdf_bytes = buf.getvalue()
    with open(filepath, "wb") as fh:
        fh.write(pdf_bytes)
    _guardar_en_archivo(session, answers, "cliente", pdf_bytes)
    return filepath


def generate_internal_pdf(session, answers: dict, result: dict) -> str:
    _ensure_dir()
    filename = f"rayosx_interno_{session.short_code}.pdf"
    filepath = os.path.join(PDF_DIR, filename)
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=0.65*inch, bottomMargin=0.65*inch,
        title=f"Rayos X INTERNO — {answers.get('institution_name','')}"
    )

    s = S()
    story = []
    metrics      = result.get("metrics", {})
    findings     = result.get("findings", [])
    is_prelim    = result.get("is_preliminary", False)
    institution  = answers.get("institution_name", "Institución")
    contact      = answers.get("contact_name", "")
    city         = answers.get("city", "")

    # Header
    story.append(Paragraph("RAYOS X INSCRIPCIONES  ·  REPORTE INTERNO  ·  SUPERLEADS", s["brand"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(institution, s["institution"]))
    meta_parts = [f"Contacto: {contact}" if contact else "", city,
                  f"Asesor: {answers.get('operator_name','')}" if answers.get('operator_name') else "",
                  f"Sesión {session.short_code}",
                  datetime.now().strftime("%d/%m/%Y")]
    story.append(Paragraph("  ·  ".join(p for p in meta_parts if p), s["tagline"]))
    story.append(Spacer(1, 6))

    # Internal warning banner
    warn = Table([[Paragraph(
        "⚠  DOCUMENTO INTERNO — NO COMPARTIR CON EL PROSPECTO",
        s["internal_warn"]
    )]], colWidths=[W_CONTENT])
    warn.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#1a2a00")),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
        ("LINEABOVE",     (0,0),(-1,0),  2, C_ACCENT),
    ]))
    story.append(warn)
    story.append(Spacer(1, 10))
    story.append(_hr())

    # Opening + funnel (same as client)
    story.append(Paragraph("Diagnóstico", s["section_title"]))
    story.append(_opening_paragraph(answers, metrics, s))
    story.append(Spacer(1, 6))
    funnel_rows = _funnel_table(metrics, s)
    if funnel_rows:
        story.extend(funnel_rows)
        story.append(Spacer(1, 10))

    # Comparison funnel
    comp_items = _comparison_funnel_pdf(metrics, answers, s)
    if comp_items:
        story.extend(comp_items)
        story.append(Spacer(1, 6))

    # Opportunity
    opp_items = _opportunity_narrative(answers, metrics, s)
    if opp_items:
        story.extend(opp_items)

    # Findings WITH solutions
    if findings:
        story.append(Paragraph("Hallazgos + mapeo comercial", s["section_title"]))
        story.append(Paragraph(
            "Para cada hallazgo: diagnóstico + causa raíz + solución SuperLeads + ángulo de demo.",
            s["muted"]
        ))
        story.append(Spacer(1, 6))
        for i, f in enumerate(findings, 1):
            story.extend(_finding_block_internal(f, i, s))

    story.append(_hr(C_BLUE, space_before=4))

    # Internal notes
    story.append(Paragraph("Notas del asesor", s["section_title"]))
    notes_data = [
        ["Notas internas",  answers.get("internal_notes", "—")],
        ["Próximo paso",    answers.get("next_step", "—")],
        ["Asesor",          answers.get("operator_name", "—")],
        ["Siguiente reunión", "Por confirmar"],
    ]
    nt = Table(
        [[Paragraph(k, s["finding_muted"]), Paragraph(v, s["finding_body"])]
         for k, v in notes_data],
        colWidths=[W_CONTENT*0.28, W_CONTENT*0.72]
    )
    nt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#06122e")),
        ("LINEBELOW",     (0,0),(-1,-2), 0.3, colors.HexColor("#0c1f60")),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
    ]))
    story.append(nt)
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}  ·  Sesión {session.short_code}  ·  "
        f"Completitud {result.get('completeness_score',0):.0f}%  ·  Certeza {result.get('certainty_score',0):.0f}%",
        s["footer"]
    ))

    doc.build(story, onFirstPage=_bg, onLaterPages=_bg)
    pdf_bytes = buf.getvalue()
    with open(filepath, "wb") as fh:
        fh.write(pdf_bytes)
    _guardar_en_archivo(session, answers, "interno", pdf_bytes)
    return filepath


def _parse_int(v):
    try:
        return int(v) if v not in (None, "", "no_se") else None
    except (ValueError, TypeError):
        return None
