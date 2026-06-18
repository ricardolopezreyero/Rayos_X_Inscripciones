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
    HRFlowable, KeepTogether, PageBreak, Flowable
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


# ── Custom Flowables ───────────────────────────────────────────────────────────

def _draw_cover(canvas, doc, institution, city, inst_type, short_code, analyzed_at):
    """Draw the full-page cover on page 1 using the canvas directly."""
    W, H = letter

    canvas.saveState()

    # ── Full background ────────────────────────────────────────────────
    canvas.setFillColor(colors.HexColor("#05103a"))
    canvas.rect(0, 0, W, H, fill=1, stroke=0)

    # ── Top strip ─────────────────────────────────────────────────────
    STRIP_H = 70  # Más alto para dar más presencia al logo
    canvas.setFillColor(colors.HexColor("#071540"))
    canvas.rect(0, H - STRIP_H, W, STRIP_H, fill=1, stroke=0)
    # Línea de acento cyan debajo del strip
    canvas.setStrokeColor(colors.HexColor("#1db2fc"))
    canvas.setLineWidth(1.5)
    canvas.line(0, H - STRIP_H, W, H - STRIP_H)

    # Logo grande en el strip superior
    logo_h = 44  # Logo mucho más grande
    logo_y = H - STRIP_H + (STRIP_H - logo_h) / 2
    logo_img = _get_logo()
    if logo_img:
        canvas.drawImage(logo_img, MARGIN, logo_y, width=logo_h, height=logo_h, mask="auto")
        text_x = MARGIN + logo_h + 10
    else:
        text_x = MARGIN

    # "SUPERLEADS" grande y prominente
    canvas.setFont("Helvetica-Bold", 18)
    canvas.setFillColor(colors.HexColor("#1db2fc"))
    canvas.drawString(text_x, logo_y + 22, "SUPERLEADS")
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(colors.HexColor("#56ef9f"))
    canvas.drawString(text_x, logo_y + 9, "RAYOS X INSCRIPCIONES")

    # ── Subtle diagonal accent lines (decorative) ──────────────────────
    canvas.setStrokeColor(colors.HexColor("#0d2260"))
    canvas.setLineWidth(0.5)
    for xi in range(0, int(W) + 60, 60):
        canvas.line(xi, H - STRIP_H, xi + 120, H - STRIP_H - 200)

    # ── Center vertical block ──────────────────────────────────────────
    center_y = H / 2 + 30

    # "DIAGNOSTICO DE INSCRIPCIONES" — label
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#56ef9f"))
    label = "D I A G N O S T I C O   D E   I N S C R I P C I O N E S"
    canvas.drawCentredString(W / 2, center_y + 90, label)

    # Institution name — up to 2 lines, large
    inst_name = institution or "Institucion"
    if len(inst_name) > 28:
        name_size = 28
    elif len(inst_name) > 20:
        name_size = 32
    else:
        name_size = 38

    canvas.setFont("Helvetica-Bold", name_size)
    canvas.setFillColor(colors.white)
    # Simple word-wrap: split at ~28 chars
    words = inst_name.split()
    lines = []
    cur_line = []
    for w in words:
        test = " ".join(cur_line + [w])
        if len(test) > 28 and cur_line:
            lines.append(" ".join(cur_line))
            cur_line = [w]
        else:
            cur_line.append(w)
    if cur_line:
        lines.append(" ".join(cur_line))

    line_h = name_size * 1.25
    name_block_h = len(lines) * line_h
    name_top = center_y + 55
    for i, ln in enumerate(lines):
        canvas.drawCentredString(W / 2, name_top - i * line_h, ln)

    # City · Type
    city_parts = []
    if city:
        city_parts.append(city)
    if inst_type:
        city_parts.append(inst_type.replace("_", " ").title())
    if city_parts:
        canvas.setFont("Helvetica", 13)
        canvas.setFillColor(colors.HexColor("#aac4ff"))
        canvas.drawCentredString(W / 2, name_top - name_block_h - 10, "  .  ".join(city_parts))

    # Green accent line
    line_y = name_top - name_block_h - 28
    canvas.setStrokeColor(colors.HexColor("#56ef9f"))
    canvas.setLineWidth(1.5)
    canvas.line(W / 2 - 120, line_y, W / 2 + 120, line_y)

    # Date · Session · Confidencial
    fecha_str = (analyzed_at or datetime.utcnow()).strftime("%d de %B de %Y").capitalize()
    meta_parts = [fecha_str, f"Sesion {short_code}", "Confidencial"]
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#3a5090"))
    canvas.drawCentredString(W / 2, line_y - 18, "  .  ".join(meta_parts))

    # ── Bottom strip ───────────────────────────────────────────────────
    BOT_H = 50
    canvas.setFillColor(colors.HexColor("#0a1e60"))
    canvas.rect(0, 0, W, BOT_H, fill=1, stroke=0)

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#3a5090"))
    canvas.drawString(MARGIN, BOT_H / 2 + 2, "Preparado por SuperLeads")
    canvas.drawCentredString(W / 2, BOT_H / 2 + 2, "Sistema de Inscripciones Educativas")
    canvas.drawRightString(W - MARGIN, BOT_H / 2 + 2, "superleads.mx")

    canvas.restoreState()


class FunnelBar(Flowable):
    """Dibuja el funnel como barras horizontales proporcionales."""

    def __init__(self, stages, width, height_per_bar=34, gap=8):
        """
        stages = [(label, value, pct_prev, pct_color), ...]
          - label: str
          - value: int
          - pct_prev: float|None  (conversion from previous stage)
          - pct_color: color object
        width: total flowable width
        """
        super().__init__()
        self.stages = stages
        self.bar_width = width
        self.height_per_bar = height_per_bar
        self.gap = gap
        self._total_h = len(stages) * (height_per_bar + gap)

    def wrap(self, availWidth, availHeight):
        return (self.bar_width, self._total_h)

    def draw(self):
        c = self.canv
        if not self.stages:
            return

        max_val = max((s[1] for s in self.stages if s[1]), default=1) or 1
        LABEL_W = 110   # left column for stage label
        PCT_W   = 60    # right column for conversion %
        BAR_ZONE = self.bar_width - LABEL_W - PCT_W - 8

        y = self._total_h - self.height_per_bar

        for i, (label, value, pct_prev, pct_color) in enumerate(self.stages):
            val = value or 0
            bar_w = BAR_ZONE * (val / max_val) if max_val else 0

            # Bar background (dim track)
            c.setFillColor(colors.HexColor("#0b1f69"))
            c.roundRect(LABEL_W, y + 4, BAR_ZONE, self.height_per_bar - 8, 4, fill=1, stroke=0)

            # Gradient feel: use two shades based on position
            t = i / max(len(self.stages) - 1, 1)
            # interpolate from C_BLUE (#2a89fb) to C_ACCENT (#56ef9f)
            r1, g1, b1 = 0x2a/255, 0x89/255, 0xfb/255
            r2, g2, b2 = 0x56/255, 0xef/255, 0x9f/255
            bar_color = colors.Color(r1 + (r2-r1)*t, g1 + (g2-g1)*t, b1 + (b2-b1)*t)

            # Filled bar
            if bar_w > 8:
                c.setFillColor(bar_color)
                c.roundRect(LABEL_W, y + 4, bar_w, self.height_per_bar - 8, 4, fill=1, stroke=0)

            # Stage label (left)
            c.setFont("Helvetica", 8.5)
            c.setFillColor(colors.HexColor("#aac4ff"))
            c.drawRightString(LABEL_W - 6, y + self.height_per_bar / 2 - 4, label)

            # Value inside bar (white, bold)
            if val > 0:
                c.setFont("Helvetica-Bold", 10)
                c.setFillColor(colors.white)
                val_x = LABEL_W + min(bar_w - 4, 12) + 4
                if bar_w < 30:
                    # put it to the right of bar
                    c.setFillColor(colors.HexColor("#edf4ff"))
                    val_x = LABEL_W + bar_w + 6
                c.drawString(val_x, y + self.height_per_bar / 2 - 4, f"{val:,}")

            # Conversion % (right side)
            if pct_prev is not None:
                pct_str = f"{pct_prev*100:.0f}%"
                c.setFont("Helvetica-Bold", 9)
                c.setFillColor(pct_color)
                c.drawString(LABEL_W + BAR_ZONE + 10, y + self.height_per_bar / 2 - 4, pct_str)
            elif i == 0:
                c.setFont("Helvetica", 7.5)
                c.setFillColor(colors.HexColor("#3a5090"))
                c.drawString(LABEL_W + BAR_ZONE + 10, y + self.height_per_bar / 2 - 4, "100%")

            y -= (self.height_per_bar + self.gap)


class JourneyBar(Flowable):
    """Visual journey bar: Diagnóstico ✓ → Diseño → Implementación → Optimización."""

    def __init__(self, width):
        super().__init__()
        self._w = width
        self._h = 56

    def wrap(self, availWidth, availHeight):
        return (self._w, self._h)

    def draw(self):
        c = self.canv
        steps = [
            ("Diagnostico", True),
            ("Diseno", False),
            ("Implementacion", False),
            ("Optimizacion", False),
        ]
        n = len(steps)
        cell_w = self._w / n

        for i, (name, done) in enumerate(steps):
            x = i * cell_w
            # background
            bg = colors.HexColor("#061a0a") if done else colors.HexColor("#081c5e")
            c.setFillColor(bg)
            c.rect(x, 0, cell_w, self._h, fill=1, stroke=0)

            # top accent line
            accent = colors.HexColor("#56ef9f") if done else colors.HexColor("#0d2070")
            c.setStrokeColor(accent)
            c.setLineWidth(2.5 if done else 0.5)
            c.line(x, self._h, x + cell_w, self._h)

            # Number/checkmark
            num_str = "v" if done else str(i + 1)
            c.setFont("Helvetica-Bold", 16)
            c.setFillColor(colors.HexColor("#56ef9f") if done else colors.HexColor("#3a5090"))
            c.drawCentredString(x + cell_w / 2, self._h / 2 + 4, num_str)

            # Label
            c.setFont("Helvetica-Bold" if done else "Helvetica", 7.5)
            c.setFillColor(colors.HexColor("#edf4ff") if done else colors.HexColor("#3a5090"))
            c.drawCentredString(x + cell_w / 2, self._h / 2 - 11, name)

            # Separator line
            if i < n - 1:
                c.setStrokeColor(colors.HexColor("#0c1f50"))
                c.setLineWidth(0.4)
                c.line(x + cell_w, 0, x + cell_w, self._h)


# ── Narrative builders ─────────────────────────────────────────────────────────
def _opening_paragraph(answers, metrics, s):
    """
    Personalized opening sentence that shows we understood their situation.
    Uses their actual numbers to make it concrete and credible.
    """
    institution = answers.get("institution_name", "su institución")
    leads       = _parse_int(metrics.get("leads"))
    enrolled    = _parse_int(metrics.get("enrolled"))
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


def _funnel_bars(metrics, s):
    """Visual funnel as horizontal bars using FunnelBar Flowable."""
    stage_defs = [
        ("Leads",           "leads",           None,                   None),
        ("Contactados",     "contacted",        "contact_rate",         None),
        ("Citas agendadas", "appointments",     "appointment_rate_leads", None),
        ("Asistentes",      "attended",         "attendance_rate",      None),
        ("Inscritos",       "enrolled",         "close_rate_attended",  None),
    ]

    stages = []
    for label, key, rate_key, _ in stage_defs:
        val = metrics.get(key)
        if val is None:
            continue
        rate = metrics.get(rate_key) if rate_key else None
        pct_color = _conv_color(rate) if rate is not None else C_MUTED
        stages.append((label, int(val), rate, pct_color))

    if len(stages) < 2:
        return []

    items = []
    # Column headers
    hdr_table = Table(
        [[
            Paragraph("Etapa", ParagraphStyle("fh", fontName="Helvetica-Bold", fontSize=8,
                      textColor=C_CYAN, alignment=TA_RIGHT)),
            Paragraph("Volumen", ParagraphStyle("fh2", fontName="Helvetica-Bold", fontSize=8,
                      textColor=C_CYAN)),
            Paragraph("Conv.", ParagraphStyle("fh3", fontName="Helvetica-Bold", fontSize=8,
                      textColor=C_CYAN)),
        ]],
        colWidths=[110, W_CONTENT - 110 - 60, 60]
    )
    hdr_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#060d2a")),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("LINEABOVE",     (0,0), (-1,0), 1, C_PANEL),
        ("LINEBELOW",     (0,0), (-1,-1), 0.4, C_PANEL),
        ("ALIGN",         (0,0), (0,-1), "RIGHT"),
    ]))
    items.append(hdr_table)
    items.append(Spacer(1, 4))
    items.append(FunnelBar(stages, W_CONTENT))
    items.append(Spacer(1, 8))
    return items


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
        [[Paragraph("  COMO LO RESUELVE SUPERLEADS", ParagraphStyle("sh",
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
        "primary":       "SOLUCION PRINCIPAL",
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
    Premium finding card for the CLIENT pdf.
    Three-section card: header (priority+zone) / body (what+why+impact) / solutions
    """
    sev_color  = _severity_color(f.get("severity_label", "Media"))
    sev_label  = f.get("severity_label", "Media").upper()
    zone       = f.get("funnel_zone", "")
    title      = f.get("title", "")
    conf_label = f.get("confidence_label", "")
    items      = []

    # ── SECTION 1: Header ─────────────────────────────────────────────────
    # Left: priority badge + title row
    # Right: zone
    num_str = f"{idx:02d}"

    priority_badge = Paragraph(
        f"● {sev_label} PRIORIDAD",
        ParagraphStyle("pb", fontName="Helvetica-Bold", fontSize=7.5,
                       textColor=sev_color, leading=10, tracking=20, spaceAfter=6)
    )
    zone_badge = Paragraph(
        f"Zona: <b>{zone}</b>" if zone else "",
        ParagraphStyle("zb", fontName="Helvetica", fontSize=7.5,
                       textColor=C_MUTED, leading=10, alignment=TA_RIGHT)
    )

    num_para = Paragraph(
        f"<b>{num_str}</b>",
        ParagraphStyle("fn", fontName="Helvetica-Bold", fontSize=28,
                       textColor=colors.HexColor("#1a3580"), leading=30, spaceAfter=0)
    )
    title_para = Paragraph(
        title,
        ParagraphStyle("ft", fontName="Helvetica-Bold", fontSize=12,
                       textColor=C_WHITE, leading=16, spaceAfter=0)
    )

    header_left = [priority_badge, num_para, title_para]
    header_right = [zone_badge]
    if conf_label:
        header_right.append(Paragraph(
            f"Certeza: <b>{conf_label}</b>",
            ParagraphStyle("cf", fontName="Helvetica", fontSize=7.5,
                           textColor=C_MUTED, leading=10, alignment=TA_RIGHT)
        ))

    ht = Table(
        [[header_left, header_right]],
        colWidths=[W_CONTENT * 0.68, W_CONTENT * 0.32]
    )
    ht.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_PANEL),
        ("LEFTPADDING",   (0,0), (-1,-1), 16),
        ("RIGHTPADDING",  (0,0), (-1,-1), 16),
        ("TOPPADDING",    (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LINEABOVE",     (0,0), (-1,0),  3, sev_color),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    items.append(ht)

    # ── SECTION 2: Body ───────────────────────────────────────────────────
    body_content = []

    # "Lo que encontramos"
    body_content.append(Paragraph(
        "LO QUE ENCONTRAMOS",
        ParagraphStyle("lh", fontName="Helvetica-Bold", fontSize=7, textColor=C_MUTED,
                       tracking=40, leading=10, spaceAfter=4)
    ))
    body_content.append(Paragraph(
        f.get("summary", ""),
        ParagraphStyle("sb", fontName="Helvetica", fontSize=9.5,
                       textColor=C_TEXT, leading=15, spaceAfter=10, alignment=TA_JUSTIFY)
    ))

    # "Por qué ocurre"
    body_content.append(Paragraph(
        "POR QUE OCURRE",
        ParagraphStyle("rh", fontName="Helvetica-Bold", fontSize=7, textColor=C_MUTED,
                       tracking=40, leading=10, spaceAfter=4)
    ))
    body_content.append(Paragraph(
        f.get("rationale", ""),
        ParagraphStyle("rb", fontName="Helvetica", fontSize=9.5,
                       textColor=C_TEXT, leading=15, spaceAfter=8, alignment=TA_JUSTIFY)
    ))

    # Estimated impact — highlight box
    if f.get("estimated_impact"):
        impact_box = Table(
            [[
                Paragraph("IMPACTO", ParagraphStyle("il", fontName="Helvetica-Bold", fontSize=7,
                           textColor=C_ACCENT, tracking=30, leading=10)),
                Paragraph(f"<b>{f['estimated_impact']}</b>",
                          ParagraphStyle("iv", fontName="Helvetica-Bold", fontSize=10,
                                         textColor=C_ACCENT, leading=13)),
            ]],
            colWidths=[72, W_CONTENT - 72 - 48]
        )
        impact_box.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#061a0a")),
            ("LINEABOVE",     (0,0), (-1,0),  1.5, C_ACCENT),
            ("LINEBELOW",     (0,0), (-1,-1), 0.4, colors.HexColor("#0f4020")),
            ("TOPPADDING",    (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING",   (0,0), (-1,-1), 12),
            ("RIGHTPADDING",  (0,0), (-1,-1), 12),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ]))
        body_content.append(impact_box)
        body_content.append(Spacer(1, 4))

    # Missing data note
    if f.get("missing_data"):
        body_content.append(Paragraph(
            f"<i>Para mayor certeza: {f['missing_data']}</i>",
            ParagraphStyle("md", fontName="Helvetica-Oblique", fontSize=8,
                           textColor=C_MUTED, leading=12, spaceAfter=4)
        ))

    body_table = Table([[body_content]], colWidths=[W_CONTENT])
    body_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#060d2a")),
        ("TOPPADDING",    (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("LEFTPADDING",   (0,0), (-1,-1), 16),
        ("RIGHTPADDING",  (0,0), (-1,-1), 16),
    ]))
    items.append(body_table)

    # ── SECTION 3: Solutions ──────────────────────────────────────────────
    items.extend(_solutions_block_client(f, s))
    items.append(Spacer(1, 16))
    return items


def _finding_block_internal(f, idx, s):
    """Finding + solutions for the INTERNAL pdf."""
    items = _finding_block_client(f, idx, s)

    solutions = f.get("solutions", [])
    if not solutions:
        return items

    role_map = {"primary": "Principal", "complementary": "Complementaria",
                "prerequisite": "Precondicion", "external": "Externo"}

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
             Paragraph(f"Demo: {sol.get('demo_angle','')}", s["sol_body"])],
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
    """
    Dirección Estratégica SuperLeads — 4 cards in a 2x2 grid layout.
    Each card has an icon, bold title, and description.
    """
    items = []

    header = Table([[
        Paragraph("★  DIRECCION ESTRATEGICA SUPERLEADS", ParagraphStyle("deh",
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
    items.append(Spacer(1, 8))

    # 4 cards in 2x2 grid
    card_specs = [
        ("●", "Sistema completo, no piezas sueltas",
         "SuperLeads diseña, instala y opera todo el Sistema de Inscripciones: CRM, "
         "procesos, formación del equipo y métricas, en un solo contrato sin intermediarios."),
        ("◈", "Estrategia + ejecución continua",
         "Acompañamiento permanente del asesor para ajustar la estrategia según los "
         "resultados reales de cada ciclo. No te deja solo después de la instalación."),
        ("→", "Decisiones con datos, no intuición",
         "Métricas del embudo en tiempo real — contactación, citas, asistencia y cierre — "
         "para saber exactamente qué palanca mover en cada momento."),
        ("★", "Resultados medibles por ciclo",
         "Compromisos claros de seguimiento: si los indicadores no avanzan, "
         "la estrategia se ajusta. El objetivo es que los números mejoren, no sólo que se midan."),
    ]

    def _make_card(icon, title, desc):
        card_content = [
            Paragraph(icon, ParagraphStyle("ci", fontName="Helvetica-Bold", fontSize=18,
                      textColor=C_ACCENT, leading=22, spaceAfter=6)),
            Paragraph(f"<b>{title}</b>", ParagraphStyle("ct", fontName="Helvetica-Bold",
                      fontSize=9.5, textColor=C_WHITE, leading=13, spaceAfter=5)),
            Paragraph(desc, ParagraphStyle("cd", fontName="Helvetica", fontSize=8.5,
                      textColor=C_TEXT, leading=13, alignment=TA_JUSTIFY)),
        ]
        card = Table([[card_content]], colWidths=[(W_CONTENT / 2) - 4])
        card.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#060f1e")),
            ("TOPPADDING",    (0,0), (-1,-1), 14),
            ("BOTTOMPADDING", (0,0), (-1,-1), 14),
            ("LEFTPADDING",   (0,0), (-1,-1), 14),
            ("RIGHTPADDING",  (0,0), (-1,-1), 14),
            ("LINEABOVE",     (0,0), (-1,0),  2, C_ACCENT),
            ("LINEBELOW",     (0,0), (-1,-1), 0.4, colors.HexColor("#0f4020")),
        ]))
        return card

    CARD_W = (W_CONTENT - 8) / 2

    # Row 1
    c1 = _make_card(*card_specs[0])
    c2 = _make_card(*card_specs[1])
    row1 = Table([[c1, c2]], colWidths=[CARD_W, CARD_W])
    row1.setStyle(TableStyle([
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("ALIGN",         (0,0), (-1,-1), "LEFT"),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    items.append(row1)
    items.append(Spacer(1, 6))

    # Row 2
    c3 = _make_card(*card_specs[2])
    c4 = _make_card(*card_specs[3])
    row2 = Table([[c3, c4]], colWidths=[CARD_W, CARD_W])
    row2.setStyle(TableStyle([
        ("LEFTPADDING",   (0,0), (-1,-1), 0),
        ("RIGHTPADDING",  (0,0), (-1,-1), 0),
        ("TOPPADDING",    (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
        ("ALIGN",         (0,0), (-1,-1), "LEFT"),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    items.append(row2)
    items.append(Spacer(1, 12))
    return items


def _executive_summary_block(answers, metrics, result, findings, s):
    """
    Página 2 — Resumen ejecutivo 'En 30 segundos'.
    1. Párrafo de apertura personalizado
    2. 4 KPI boxes en fila
    3. Hallazgo #1 en highlight
    """
    items = []

    # Title
    items.append(Paragraph(
        "E N   3 0   S E G U N D O S",
        ParagraphStyle("exec_label", fontName="Helvetica-Bold", fontSize=8,
                       textColor=C_ACCENT, tracking=20, leading=12, spaceAfter=6)
    ))

    # Opening paragraph
    items.append(_opening_paragraph(answers, metrics, s))
    items.append(Spacer(1, 10))

    # 4 KPI boxes
    certainty    = result.get("certainty_score", 0)
    leads        = _parse_int(metrics.get("leads"))
    close_rate   = metrics.get("close_rate_attended")
    if close_rate is None:
        close_rate = metrics.get("enroll_rate")
    gap          = metrics.get("gap_to_target")
    recoverable  = result.get("total_recoverable", {})

    # El 4º KPI prioriza el potencial recuperable (limpio); si no hay, muestra la brecha.
    if recoverable.get("students"):
        kpi4 = (f"+{_fmt(recoverable['students'])}", "Alumnos\nrecuperables")
    elif gap and gap > 0:
        kpi4 = (_fmt(gap), "Alumnos de brecha\nhacia la meta")
    else:
        kpi4 = ("—", "Alumnos de brecha\nhacia la meta")

    kpi_data = [
        (f"{certainty:.0f}%",           "Certeza del\ndiagnóstico"),
        (_fmt(leads) if leads else "—",  "Leads\nanuales"),
        (_pct(close_rate),               "Tasa de cierre\nreal"),
        kpi4,
    ]

    kpi_cells = []
    for val, lbl in kpi_data:
        kpi_cells.append([
            Paragraph(val, ParagraphStyle("kv", fontName="Helvetica-Bold", fontSize=20,
                       textColor=C_ACCENT, leading=24, alignment=TA_CENTER)),
            Paragraph(lbl, ParagraphStyle("kl", fontName="Helvetica", fontSize=7.5,
                       textColor=C_MUTED, leading=10, alignment=TA_CENTER)),
        ])

    kpi_w = W_CONTENT / 4
    kt = Table([kpi_cells], colWidths=[kpi_w] * 4)
    kt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#0b1f69")),
        ("GRID",          (0,0), (-1,-1), 0.5, colors.HexColor("#0d2070")),
        ("TOPPADDING",    (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
        ("LINEABOVE",     (0,0), (-1,0),  2, C_ACCENT),
    ]))
    items.append(kt)
    items.append(Spacer(1, 14))

    # ── Franja estrella: potencial recuperable (número honesto, sin doble conteo) ──
    if recoverable.get("students"):
        students = recoverable["students"]
        money    = recoverable.get("money")
        cur_enr  = _parse_int(metrics.get("enrolled"))
        if money:
            headline = (
                f"Llevando cada etapa del embudo al estándar SuperLeads, tu sistema "
                f"actual podría sumar <b><font color='#56ef9f'>≈ {students:,} alumnos más al año</font></b> "
                f"(<b><font color='#56ef9f'>${money:,.0f}</font></b> en colegiaturas) — "
                f"con los mismos leads que ya entran."
            )
        else:
            headline = (
                f"Llevando cada etapa del embudo al estándar SuperLeads, tu sistema "
                f"actual podría sumar <b><font color='#56ef9f'>≈ {students:,} alumnos más al año</font></b> — "
                f"con los mismos leads que ya entran."
            )
        star = Table([[
            Paragraph(headline, ParagraphStyle("star", fontName="Helvetica", fontSize=10.5,
                       textColor=C_WHITE, leading=16))
        ]], colWidths=[W_CONTENT])
        star.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#06231a")),
            ("TOPPADDING",    (0,0), (-1,-1), 14),
            ("BOTTOMPADDING", (0,0), (-1,-1), 14),
            ("LEFTPADDING",   (0,0), (-1,-1), 16),
            ("RIGHTPADDING",  (0,0), (-1,-1), 16),
            ("LINEABOVE",     (0,0), (-1,0),  2, C_ACCENT),
            ("LINEBELOW",     (0,0), (-1,-1), 2, C_ACCENT),
        ]))
        items.append(star)
        items.append(Paragraph(
            "Estimación conservadora basada en tus propios números, acotada por tu cupo disponible. "
            "No es una proyección garantizada — es el techo realista del sistema actual.",
            ParagraphStyle("star_note", fontName="Helvetica-Oblique", fontSize=7.5,
                           textColor=C_MUTED, leading=11, spaceBefore=4)
        ))
        items.append(Spacer(1, 14))

    # Hallazgo #1 en highlight
    if findings:
        f1        = findings[0]
        sev_color = _severity_color(f1.get("severity_label", "Alta"))
        hi_box    = Table([[
            Paragraph(
                f"<b>Hallazgo #1 — {f1.get('title','')}</b><br/>"
                f"<font color='#aac4ff'>{f1.get('summary','')[:180]}{'...' if len(f1.get('summary','')) > 180 else ''}</font>",
                ParagraphStyle("h1", fontName="Helvetica", fontSize=9.5,
                               textColor=C_WHITE, leading=15)
            ),
        ]], colWidths=[W_CONTENT])
        hi_box.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#061a0a")),
            ("TOPPADDING",    (0,0), (-1,-1), 14),
            ("BOTTOMPADDING", (0,0), (-1,-1), 14),
            ("LEFTPADDING",   (0,0), (-1,-1), 16),
            ("RIGHTPADDING",  (0,0), (-1,-1), 16),
            ("LINEABOVE",     (0,0), (-1,0),  3, sev_color),
            ("LINEBELOW",     (0,0), (-1,-1), 0.5, colors.HexColor("#0f4020")),
        ]))
        items.append(Paragraph(
            "HALLAZGO PRINCIPAL",
            ParagraphStyle("hl_lbl", fontName="Helvetica-Bold", fontSize=7,
                           textColor=C_MUTED, tracking=40, leading=10, spaceAfter=4)
        ))
        items.append(hi_box)
        items.append(Spacer(1, 8))

    return items


def _closing_page(s, is_preliminary=False):
    """
    Página final de CTA dedicada — página completa oscura con journey bar,
    mensaje final y link del calendario.
    """
    items = []
    items.append(PageBreak())

    # Big headline
    items.append(Spacer(1, 30))
    items.append(Paragraph(
        "El diagnóstico está completo.",
        ParagraphStyle("cl_big", fontName="Helvetica-Bold", fontSize=24,
                       textColor=C_WHITE, leading=30, alignment=TA_CENTER, spaceAfter=12)
    ))
    items.append(Paragraph(
        "El siguiente paso es diseñar la solución exacta para tu caso.",
        ParagraphStyle("cl_sub", fontName="Helvetica", fontSize=13,
                       textColor=C_MUTED, leading=18, alignment=TA_CENTER, spaceAfter=30)
    ))

    # Journey bar visual (custom Flowable)
    items.append(JourneyBar(W_CONTENT))
    items.append(Spacer(1, 28))

    if is_preliminary:
        msg = (
            "Este es un diagnóstico preliminar basado en los datos disponibles. "
            "Tiene suficiente claridad para arrancar una conversación productiva, "
            "pero se fortalece con más datos del embudo completo."
        )
    else:
        msg = (
            "La siguiente conversación no es una propuesta comercial genérica — "
            "es diseñar exactamente qué intervención resuelve cada cuello detectado, "
            "en el orden de prioridad que el propio sistema reveló."
        )

    items.append(Paragraph(
        msg,
        ParagraphStyle("cl_body", fontName="Helvetica", fontSize=10,
                       textColor=C_MUTED, leading=16, alignment=TA_CENTER, spaceAfter=28)
    ))

    # Big CTA box
    cta_box = Table([[
        Paragraph(
            f"Agenda tu Diseño de Solución<br/>"
            f"<b><font color='#56ef9f'>{CALENDAR_URL}</font></b>",
            ParagraphStyle("cta_url", fontName="Helvetica", fontSize=11,
                           textColor=C_TEXT, leading=20, alignment=TA_CENTER)
        )
    ]], colWidths=[W_CONTENT])
    cta_box.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#061a0a")),
        ("TOPPADDING",    (0,0), (-1,-1), 22),
        ("BOTTOMPADDING", (0,0), (-1,-1), 22),
        ("LEFTPADDING",   (0,0), (-1,-1), 24),
        ("RIGHTPADDING",  (0,0), (-1,-1), 24),
        ("LINEABOVE",     (0,0), (-1,0),  2.5, C_ACCENT),
        ("LINEBELOW",     (0,0), (-1,-1), 2.5, C_ACCENT),
        ("LINEBEFORE",    (0,0), (-1,-1), 0.5, colors.HexColor("#0f4020")),
        ("LINEAFTER",     (0,0), (-1,-1), 0.5, colors.HexColor("#0f4020")),
    ]))
    items.append(cta_box)
    items.append(Spacer(1, 20))

    items.append(Paragraph(
        "<i>SuperLeads no vende piezas sueltas. Diseña y opera el Sistema de Inscripciones completo.</i>",
        ParagraphStyle("cl_callout", fontName="Helvetica-BoldOblique", fontSize=10,
                       textColor=C_WHITE, leading=16, alignment=TA_CENTER, spaceAfter=8)
    ))

    items.append(Spacer(1, 16))
    items.append(Paragraph(
        f"superleads.mx  ·  Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}  ·  Confidencial",
        ParagraphStyle("cl_footer", fontName="Helvetica", fontSize=7.5,
                       textColor=colors.HexColor("#3a5090"),
                       alignment=TA_CENTER, leading=11)
    ))

    # ── Página final de marca ─────────────────────────────────────────────
    items.append(PageBreak())
    items.append(_brand_closing_page())

    return items


class _BrandClosingPage(Flowable):
    """Página de cierre de marca: frase icónica + logo SuperLeads grande."""

    def __init__(self, width, height):
        super().__init__()
        self.width  = width
        self.height = height

    def wrap(self, aw, ah):
        return (self.width, self.height)

    def draw(self):
        c    = self.canv
        W, H = letter
        # Usa el espacio del área de contenido — calculamos posiciones absolutas
        content_w = self.width

        # ── Frase principal ───────────────────────────────────────────────
        # Centrada verticalmente en la zona de contenido
        mid = self.height / 2

        # Línea decorativa superior
        c.setStrokeColor(colors.HexColor("#1db2fc"))
        c.setLineWidth(0.8)
        c.line(0, mid + 110, content_w, mid + 110)

        # La frase
        c.setFont("Helvetica-Bold", 22)
        c.setFillColor(colors.HexColor("#edf4ff"))
        # Partir en 2 líneas naturales
        line1 = "Un buen anuncio no reemplaza"
        line2 = "un mal seguimiento."
        c.drawCentredString(content_w / 2, mid + 70, line1)
        c.setFillColor(colors.HexColor("#56ef9f"))
        c.drawCentredString(content_w / 2, mid + 40, line2)

        # Línea decorativa inferior
        c.setStrokeColor(colors.HexColor("#56ef9f"))
        c.setLineWidth(1.5)
        c.line(content_w / 2 - 80, mid + 22, content_w / 2 + 80, mid + 22)

        # ── Logo grande centrado ──────────────────────────────────────────
        logo_img = _get_logo()
        logo_size = 80  # Logo imponente
        logo_x = content_w / 2 - logo_size / 2
        logo_y = mid - 90

        if logo_img:
            c.drawImage(logo_img, logo_x, logo_y,
                        width=logo_size, height=logo_size, mask="auto")

        # "SUPERLEADS" bajo el logo
        c.setFont("Helvetica-Bold", 26)
        c.setFillColor(colors.HexColor("#1db2fc"))
        c.drawCentredString(content_w / 2, logo_y - 28, "SUPERLEADS")

        # Tagline
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.HexColor("#aac4ff"))
        c.drawCentredString(content_w / 2, logo_y - 44,
                            "Sistema de Inscripciones Educativas")

        # URL
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#56ef9f"))
        c.drawCentredString(content_w / 2, logo_y - 58, "superleads.mx")


def _brand_closing_page():
    """Devuelve el Flowable de la página de cierre de marca."""
    content_w = W_CONTENT
    # Altura del frame interior (letra menos márgenes del doc)
    content_h = letter[1] - 2 * (0.65 * inch) - 0.38 * inch  # descontar header strip
    return _BrandClosingPage(content_w, content_h)


# ── Main PDF generators ────────────────────────────────────────────────────────
def generate_client_pdf(session, answers: dict, result: dict) -> str:
    _ensure_dir()
    filename = f"rayosx_cliente_{session.short_code}.pdf"
    filepath = os.path.join(PDF_DIR, filename)
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=0.65 * inch, bottomMargin=0.65 * inch,
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
    inst_type      = answers.get("institution_type", "")
    analyzed_at    = getattr(session, "analyzed_at", None)

    # ── Page 1: Cover (drawn entirely via onFirstPage callback) ────────────
    # Just a PageBreak to push content to page 2; the cover is drawn by the canvas callback.
    story.append(PageBreak())

    # ── Page 2: Executive Summary ──────────────────────────────────────────
    story.extend(_executive_summary_block(answers, metrics, result, findings, s))
    story.append(_hr(C_BLUE, thickness=0.4))

    if is_preliminary:
        story.append(Paragraph(
            "Diagnostico preliminar — datos suficientes para identificar el patrón principal, "
            "pero con certeza reducida. Más datos del embudo elevarían la confianza.",
            ParagraphStyle("warn", fontName="Helvetica-BoldOblique", fontSize=9,
                           textColor=C_YELLOW, leading=14, spaceAfter=6,
                           backColor=colors.HexColor("#1a1200"),
                           leftIndent=8, rightIndent=8,
                           borderPad=6)
        ))

    # ── Funnel bars ────────────────────────────────────────────────────────
    funnel_rows = _funnel_bars(metrics, s)
    if funnel_rows:
        story.append(Paragraph("El embudo, con sus fugas", s["section_title"]))
        story.append(Paragraph(
            "Cada barra muestra qué tan lejos llega un prospecto antes de perderse. "
            "El porcentaje de la derecha indica la conversión desde la etapa anterior.",
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

    # ── Dirección Estratégica — 2x2 grid ──────────────────────────────────
    story.append(Paragraph("La recomendación del sistema", s["section_title"]))
    story.extend(_strategic_direction_block(s))

    # ── Page final: CTA dedicada ───────────────────────────────────────────
    story.extend(_closing_page(s, is_preliminary))

    # ── Build ──────────────────────────────────────────────────────────────
    def _first_page(canvas, doc):
        """Page 1: draw the full premium cover."""
        _draw_cover(
            canvas, doc,
            institution=institution,
            city=city,
            inst_type=inst_type,
            short_code=session.short_code,
            analyzed_at=analyzed_at,
        )

    def _later_pages(canvas, doc):
        _bg(canvas, doc)

    doc.build(story, onFirstPage=_first_page, onLaterPages=_later_pages)
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
        "DOCUMENTO INTERNO — NO COMPARTIR CON EL PROSPECTO",
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
    funnel_rows = _funnel_bars(metrics, s)
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
