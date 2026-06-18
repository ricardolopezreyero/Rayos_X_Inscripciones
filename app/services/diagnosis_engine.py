"""Deterministic diagnosis engine — no LLM required for core logic.

Modelo del embudo (cascada):
    leads → contactados → citas → asistentes → inscritos

Cada hallazgo incluye, cuando hay datos suficientes, una estimación
económica conservadora de lo recuperable (alumnos/año y $/año),
acotada por la capacidad disponible de la institución.
"""
from __future__ import annotations
import yaml
import os
from typing import Optional

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../../config/diagnostic_rules.yaml")
SOLUTIONS_PATH = os.path.join(os.path.dirname(__file__), "../../config/solutions.yaml")

_rules = None
_solutions = None


def _load_rules():
    global _rules
    if _rules is None:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            _rules = yaml.safe_load(f)
    return _rules


def _load_solutions():
    global _solutions
    if _solutions is None:
        with open(SOLUTIONS_PATH, "r", encoding="utf-8") as f:
            _solutions = yaml.safe_load(f)
    return _solutions


def _safe_div(num, den):
    if den and den > 0 and num is not None:
        return num / den
    return None


def _parse_int(v) -> Optional[int]:
    try:
        return int(float(v)) if v not in (None, "", "no_se") else None
    except (ValueError, TypeError):
        return None


def compute_funnel_metrics(answers: dict) -> dict:
    """Derive conversion rates from raw funnel numbers."""
    funnel_keys = ["impressions", "reach", "clicks", "leads", "contacted", "appointments", "attended", "enrolled"]
    vals = {}
    quals = {}
    for k in funnel_keys:
        vals[k] = _parse_int(answers.get(k))
        quals[k] = answers.get(f"quality_{k}", "approximate")

    m = {}

    m["leads"] = vals["leads"]
    m["enrolled"] = vals["enrolled"]
    m["contacted"] = vals["contacted"]
    m["appointments"] = vals["appointments"]
    m["attended"] = vals["attended"]
    m["impressions"] = vals["impressions"]
    m["clicks"] = vals["clicks"]

    # ── Tasas de conversión (cada etapa sobre la anterior) ────────────────
    # Se acotan a [0,1]: una tasa de conversión > 100% siempre viene de datos
    # incoherentes (p.ej. inscritos > asistentes) y rompería las proyecciones.
    def _rate(num, den):
        r = _safe_div(num, den)
        return min(1.0, max(0.0, r)) if r is not None else None

    m["contact_rate"] = _rate(vals["contacted"], vals["leads"])
    m["appointment_rate_contacted"] = _rate(vals["appointments"], vals["contacted"])
    m["appointment_rate_leads"] = _rate(vals["appointments"], vals["leads"])
    m["attendance_rate"] = _rate(vals["attended"], vals["appointments"])
    m["no_show_rate"] = (1 - m["attendance_rate"]) if m["attendance_rate"] is not None else None
    m["enroll_rate"] = _rate(vals["enrolled"], vals["leads"])
    m["close_rate_attended"] = _rate(vals["enrolled"], vals["attended"])
    m["close_rate_appointments"] = _rate(vals["enrolled"], vals["appointments"])
    m["ctr"] = _rate(vals["clicks"], vals["impressions"])

    # Señal de incoherencia: alguna etapa supera a la anterior
    incoherent = False
    chain = [vals["leads"], vals["contacted"], vals["appointments"], vals["attended"], vals["enrolled"]]
    prev = None
    for v in chain:
        if v is not None:
            if prev is not None and v > prev:
                incoherent = True
            prev = v
    m["funnel_incoherent"] = incoherent

    # ── Fugas en números absolutos ────────────────────────────────────────
    if vals["leads"] and vals["contacted"] is not None:
        m["leak_lead_to_contacted"] = max(0, vals["leads"] - vals["contacted"])
    if vals["contacted"] and vals["appointments"] is not None:
        m["leak_contacted_to_appointment"] = max(0, vals["contacted"] - vals["appointments"])
    if vals["appointments"] and vals["attended"] is not None:
        m["leak_appointment_to_attended"] = max(0, vals["appointments"] - vals["attended"])
    if vals["attended"] and vals["enrolled"] is not None:
        m["leak_attended_to_enrolled"] = max(0, vals["attended"] - vals["enrolled"])
    if vals["leads"] and vals["enrolled"] is not None:
        m["lost_prospects"] = max(0, vals["leads"] - vals["enrolled"])

    # ── Contexto económico ────────────────────────────────────────────────
    # Valores ≤ 0 son inputs inválidos → se tratan como ausentes.
    ticket = _parse_int(answers.get("average_ticket"))
    if ticket is not None and ticket <= 0:
        ticket = None
    capacity = _parse_int(answers.get("max_capacity"))
    if capacity is not None and capacity <= 0:
        capacity = None
    enrollment = _parse_int(answers.get("current_enrollment"))
    target = _parse_int(answers.get("target_new_enrollments"))
    if target is not None and target <= 0:
        target = None

    m["ticket"] = ticket
    if capacity and enrollment is not None:
        m["capacity_available"] = max(0, capacity - enrollment)

    if target:
        if vals["enrolled"] is not None:
            m["gap_to_target"] = target - vals["enrolled"]
        else:
            m["gap_to_target"] = target

    # Oportunidad: lo realista — brecha a la meta acotada por cupo físico
    if ticket:
        cap = m.get("capacity_available")
        gap = m.get("gap_to_target")
        if gap and gap > 0:
            realistic = min(gap, cap) if cap is not None else gap
            m["opportunity_value"] = realistic * ticket
        elif cap:
            m["opportunity_value"] = cap * ticket

    m["data_quality"] = {k: quals[k] for k in funnel_keys}
    return m


def _compute_completeness(answers: dict, metrics: dict) -> float:
    """0-100 score based on key fields present."""
    def has(field):
        v = answers.get(field)
        return bool(v) and str(v).strip() not in ("", "no_se", "no_lo_se")

    def has_prefix(prefix):
        return any(k.startswith(prefix) and answers.get(k) for k in answers)

    weighted = [
        (has("leads"), 15), (has("enrolled"), 15), (has("appointments"), 10),
        (has("first_contact_delay_bucket"), 8), (has("uses_crm"), 7),
        (has("channels_integrated"), 7),
        (has_prefix("obj_") or has("objections_list") or has("top_2_objections_text"), 6),
        (has("max_capacity"), 5), (has("target_new_enrollments"), 5),
        (has("contacted"), 8), (has("attended"), 5), (has("average_ticket"), 5),
        (has("institution_name"), 4),
    ]
    total = sum(w for _, w in weighted)
    score = sum(w for ok, w in weighted if ok)
    return min(100.0, (score / total) * 100)


def _first_response_delay_minutes(bucket: str) -> Optional[int]:
    mapping = {
        "menos_5": 3, "5_15": 10, "15_60": 40,
        "1_3h": 120, "mas_3h": 360, "no_medimos": 500,
    }
    return mapping.get(bucket)


# ──────────────────────────────────────────────────────────────────────────────
# Estimación económica: alumnos adicionales → $ anuales, acotado por capacidad
# ──────────────────────────────────────────────────────────────────────────────

def _rate_or(metrics: dict, key: str, bench: dict) -> float:
    """Devuelve la tasa real si existe (incluido 0.0); si es None usa benchmark.
    NO usa `or` para no confundir 0.0 (dato válido) con ausencia de dato."""
    v = metrics.get(key)
    return v if v is not None else bench[key]


def _downstream_to_enrolled(metrics: dict, bench: dict, from_stage: str) -> float:
    """Probabilidad de que un prospecto en `from_stage` termine inscrito.
    Usa las tasas reales de la institución; si faltan, benchmarks conservadores."""
    appt  = _rate_or(metrics, "appointment_rate_contacted", bench)
    att   = _rate_or(metrics, "attendance_rate", bench)
    close = _rate_or(metrics, "close_rate_attended", bench)
    if from_stage == "contacted":
        return appt * att * close
    if from_stage == "appointments":
        return att * close
    if from_stage == "attended":
        return close
    return appt * att * close  # default


def _impact(extra_students: float, metrics: dict) -> dict:
    """Acota por capacidad disponible y convierte a pesos."""
    if extra_students is None or extra_students <= 0:
        return {}
    cap = metrics.get("capacity_available")
    students = int(round(min(extra_students, cap) if cap is not None else extra_students))
    if students <= 0:
        return {}
    out = {"impact_students": students}
    ticket = metrics.get("ticket")
    if ticket:
        out["impact_money"] = students * ticket
        out["estimated_impact"] = (
            f"Corregir solo esta etapa: ≈ {students:,} alumnos/año "
            f"(${students * ticket:,.0f})"
        )
    else:
        out["estimated_impact"] = f"Corregir solo esta etapa: ≈ {students:,} alumnos/año"
    return out


def _compute_total_recoverable(metrics: dict, bench: dict) -> dict:
    """Inscritos adicionales si cada métrica del embudo sube AL MENOS al benchmark.

    Recalcula el embudo completo (sin doble conteo entre palancas) y compara con
    los inscritos actuales. Acota por capacidad disponible y convierte a pesos.
    Solo aplica si hay leads y al menos el dato de inscritos.
    """
    leads = metrics.get("leads")
    enrolled = metrics.get("enrolled")
    ticket = metrics.get("ticket")
    if not leads or enrolled is None:
        return {}

    # Cada tasa se lleva al máximo entre la actual y el benchmark (nunca empeora).
    cr = max(_rate_or(metrics, "contact_rate", bench), bench["contact_rate"])
    ar = max(_rate_or(metrics, "appointment_rate_contacted", bench), bench["appointment_rate_contacted"])
    tr = max(_rate_or(metrics, "attendance_rate", bench), bench["attendance_rate"])
    clr = max(_rate_or(metrics, "close_rate_attended", bench), bench["close_rate_attended"])

    enrolled_potential = leads * cr * ar * tr * clr
    extra = enrolled_potential - enrolled
    if extra <= 0:
        return {}

    cap = metrics.get("capacity_available")
    students = int(round(min(extra, cap) if cap is not None else extra))
    if students <= 0:
        return {}

    out = {"students": students}
    if ticket:
        out["money"] = students * ticket
    return out


def run_diagnosis(answers: dict) -> dict:
    rules = _load_rules()
    solutions = _load_solutions()["solutions"]
    thresholds = rules["thresholds"]
    bench = rules.get("benchmarks", {
        "contact_rate": 0.65, "appointment_rate_contacted": 0.40,
        "attendance_rate": 0.70, "close_rate_attended": 0.45,
        "after_hours_lead_share": 0.35, "slow_response_appointment_loss": 0.40,
    })

    metrics = compute_funnel_metrics(answers)
    completeness = _compute_completeness(answers, metrics)
    is_preliminary = completeness < 30

    findings = []

    leads        = metrics.get("leads")
    contacted    = metrics.get("contacted")
    appointments = metrics.get("appointments")
    attended     = metrics.get("attended")
    enrolled     = metrics.get("enrolled")
    ticket       = metrics.get("ticket")
    target       = _parse_int(answers.get("target_new_enrollments"))

    def _q(stage):
        return metrics["data_quality"].get(stage, "approximate")

    # ═══ A. Volumen insuficiente de prospectos ════════════════════════════
    if leads is not None and target:
        # Leads necesarios para la meta con la conversión actual (o benchmark)
        conv = metrics.get("enroll_rate")
        if not conv or conv <= 0:
            conv = (bench["contact_rate"] * bench["appointment_rate_contacted"]
                    * bench["attendance_rate"] * bench["close_rate_attended"])
        leads_needed = target / conv if conv > 0 else None

        if leads_needed and leads < leads_needed:
            ratio = leads / leads_needed  # < 1 = faltan leads
            sev_score = min(92, 50 + (1 - ratio) * 40)
            conf_score = 75.0 if _q("leads") == "exact" else 60.0
            faltan = int(leads_needed - leads)

            findings.append({
                "code": "low_volume",
                "title": "Volumen insuficiente de prospectos",
                "type": "primary_bottleneck",
                "funnel_zone": "Atracción",
                "affected_stage": "leads",
                "affected_transition": "mercado → leads",
                "severity_score": round(sev_score, 1),
                "severity_label": "Alta" if sev_score >= 65 else "Media",
                "confidence_score": round(conf_score, 1),
                "confidence_label": "Alta" if conf_score >= 65 else "Media",
                "summary": (
                    f"Con la conversión actual ({(conv*100):.1f}%), alcanzar la meta de "
                    f"{target:,} inscritos requiere ≈ {int(leads_needed):,} leads/año. "
                    f"Hoy entran {leads:,} — faltan ≈ {faltan:,}."
                ),
                "rationale": (
                    "Aunque el proceso convirtiera bien, el volumen de entrada no alcanza "
                    "para la meta. Crecer requiere más prospectos calificados o una mejora "
                    "fuerte de conversión — idealmente ambas."
                ),
                "evidence": [
                    f"Leads/año: {leads:,}",
                    f"Leads necesarios para la meta: ≈ {int(leads_needed):,}",
                    f"Conversión global actual: {(conv*100):.1f}%",
                ],
                "missing_data": "Inversión actual en campañas y costo por lead",
                "root_cause": "low_volume",
                "solutions": _map_solutions(solutions, "low_volume", rules),
                **_impact(min(faltan * conv, (target - (enrolled or 0))), metrics),
            })

    # ═══ B. Baja contactación ═════════════════════════════════════════════
    contact_rate = metrics.get("contact_rate")
    if contact_rate is not None and contact_rate < thresholds["low_contact_rate"]:
        delay_bucket = answers.get("first_contact_delay_bucket", "")
        delay_min = _first_response_delay_minutes(delay_bucket)
        slow_response = delay_min and delay_min >= thresholds["slow_first_response_minutes"]

        sev_score = min(92, 55 + (thresholds["low_contact_rate"] - contact_rate) * 100)
        conf_base = 0.80 if _q("contacted") == "exact" else 0.65
        if slow_response:
            conf_base = min(0.90, conf_base + 0.10)

        # Recuperable: subir contactación al benchmark
        extra_contacted = leads * (bench["contact_rate"] - contact_rate) if leads else 0
        extra_enrolled = extra_contacted * _downstream_to_enrolled(metrics, bench, "contacted")

        root = "slow_response" if slow_response else "fragmented_channels"
        findings.append({
            "code": "low_contactation",
            "title": "Baja tasa de contactación",
            "type": "primary_bottleneck",
            "funnel_zone": "Admisión",
            "affected_stage": "contacted",
            "affected_transition": "leads → contactados",
            "severity_score": round(sev_score, 1),
            "severity_label": "Alta" if sev_score >= 65 else "Media",
            "confidence_score": round(conf_base * 100, 1),
            "confidence_label": "Alta" if conf_base >= 0.65 else "Media",
            "summary": (
                f"Solo {contact_rate*100:.0f}% de los leads recibe una respuesta efectiva. "
                f"De {leads:,} leads, {int(leads*(1-contact_rate)):,} nunca tienen una conversación real."
                if leads else
                f"Solo {contact_rate*100:.0f}% de los leads recibe una respuesta efectiva."
            ),
            "rationale": (
                f"Con primera respuesta de '{delay_bucket.replace('_',' ')}', muchos prospectos "
                "se enfrían antes del primer contacto. La fuga más cara es la que ocurre antes de hablar."
                if slow_response else
                "Los leads no están siendo atendidos de forma sistemática — sin proceso de "
                "respuesta y reintento, gran parte del presupuesto de captación se desperdicia."
            ),
            "evidence": [
                f"Tasa de contactación: {contact_rate*100:.1f}%",
                f"Benchmark mínimo: {thresholds['low_contact_rate']*100:.0f}% · Benchmark SuperLeads: {bench['contact_rate']*100:.0f}%",
            ],
            "missing_data": "Medición de tiempos de respuesta por asesor",
            "root_cause": root,
            "solutions": _map_solutions(solutions, root, rules),
            **_impact(extra_enrolled, metrics),
        })

    # ═══ C. Respuesta lenta (independiente de contactación) ══════════════
    delay_bucket = answers.get("first_contact_delay_bucket", "")
    delay_min = _first_response_delay_minutes(delay_bucket)
    already_flagged_speed = any(f["root_cause"] == "slow_response" for f in findings)
    if delay_min and delay_min >= thresholds["slow_first_response_minutes"] and not already_flagged_speed:
        no_measure = delay_bucket == "no_medimos"
        sev_score = 80.0 if delay_min >= thresholds["critical_first_response_minutes"] else 68.0
        conf_score = 60.0 if no_measure else 78.0

        # Citas recuperables por responder rápido — estimación conservadora.
        # Asumimos que solo una fracción de los leads llega "lento" (~50%) y que
        # de esos se recupera la pérdida de cita del benchmark. Evita sobreestimar
        # asumiendo que TODO el embudo sufre la lentitud.
        slow_lead_fraction = 0.5
        recover_rate = bench["slow_response_appointment_loss"] * slow_lead_fraction  # 0.40 × 0.50 = 0.20
        extra_appts = (appointments or 0) * recover_rate
        extra_enrolled = extra_appts * _downstream_to_enrolled(metrics, bench, "appointments")

        findings.append({
            "code": "slow_first_response",
            "title": "Primera respuesta demasiado lenta" if not no_measure else "No miden el tiempo de primera respuesta",
            "type": "primary_bottleneck",
            "funnel_zone": "Admisión",
            "affected_stage": "contacted",
            "affected_transition": "leads → contactados",
            "severity_score": sev_score,
            "severity_label": "Alta",
            "confidence_score": conf_score,
            "confidence_label": "Alta" if conf_score >= 65 else "Media",
            "summary": (
                "Nadie sabe cuánto tarda la primera respuesta — y lo que no se mide, no se corrige. "
                "La experiencia muestra que cuando no se mide, casi siempre supera 1 hora."
                if no_measure else
                f"La primera respuesta tarda '{delay_bucket.replace('_',' ')}'. "
                "Responder después de 60 minutos reduce la probabilidad de cita en más del 40%."
            ),
            "rationale": (
                "El prospecto que escribe a 3 escuelas se queda con la primera que responde bien. "
                "La velocidad de respuesta es la palanca más barata y rápida de mover en todo el embudo."
            ),
            "evidence": [
                f"Primera respuesta: {delay_bucket.replace('_',' ')}",
                "Benchmark: < 5 minutos con sistema automatizado",
            ],
            "missing_data": "Tiempos de respuesta reales por canal y por asesor",
            "root_cause": "slow_response",
            "solutions": _map_solutions(solutions, "slow_response", rules),
            **_impact(extra_enrolled, metrics),
        })

    # ═══ D. Fuga fuera de horario ═════════════════════════════════════════
    sched_247  = answers.get("sched_247") == "si" or answers.get("lead_attention_schedule") == "24_7"
    sched_ext  = answers.get("sched_tarde") == "si" or answers.get("sched_finde") == "si" \
                 or answers.get("lead_attention_schedule") in ("horario_ampliado", "fines_semana")
    coverage   = answers.get("after_hours_coverage", "")
    # Requiere que el usuario haya respondido el horario o la cobertura — no inventa
    # con formulario vacío. Y que haya al menos volumen de leads para estimar.
    answered_schedule = bool(answers.get("lead_attention_schedule")) or \
        any(answers.get(k) for k in ("sched_oficina", "sched_tarde", "sched_finde", "sched_247"))
    office_only = not sched_247 and not sched_ext
    if office_only and coverage in ("no", "parcial") and answered_schedule and leads:
        share = bench["after_hours_lead_share"]
        sev_score = 72.0 if coverage == "no" else 62.0
        # Leads fuera de horario sin atender; recuperación conservadora del 50%
        missed = (leads or 0) * share * (1.0 if coverage == "no" else 0.5)
        extra_enrolled = missed * 0.5 * _downstream_to_enrolled(metrics, bench, "contacted")

        findings.append({
            "code": "after_hours_leak",
            "title": "Fuga de prospectos fuera de horario",
            "type": "primary_bottleneck",
            "funnel_zone": "Admisión",
            "affected_stage": "contacted",
            "affected_transition": "leads → contactados",
            "severity_score": sev_score,
            "severity_label": "Alta" if sev_score >= 65 else "Media",
            "confidence_score": 70.0,
            "confidence_label": "Alta",
            "summary": (
                f"≈ {share*100:.0f}% de los prospectos escribe por la tarde-noche o en fin de semana — "
                "exactamente cuando nadie atiende. Esos leads encuentran respuesta en otra institución."
            ),
            "rationale": (
                "Las familias investigan opciones educativas cuando salen del trabajo. "
                "Atender solo en horario de oficina deja la ventana de mayor intención sin cobertura."
            ),
            "evidence": [
                "Atención solo en horario de oficina",
                f"Cobertura fuera de horario: {coverage or 'sin definir'}",
            ],
            "missing_data": "Distribución horaria real de los leads entrantes",
            "root_cause": "after_hours_leak",
            "solutions": _map_solutions(solutions, "after_hours_leak", rules),
            **_impact(extra_enrolled, metrics),
        })

    # ═══ E. Baja conversión a citas ═══════════════════════════════════════
    appt_rate_c = metrics.get("appointment_rate_contacted")
    if appt_rate_c is not None and appt_rate_c < thresholds["low_appointment_rate_contacted"]:
        sev_score = min(88, 50 + (thresholds["low_appointment_rate_contacted"] - appt_rate_c) * 150)
        conf_score = 70.0 if _q("appointments") in ("exact", "approximate") else 50.0

        extra_appts = (contacted or 0) * (bench["appointment_rate_contacted"] - appt_rate_c)
        extra_enrolled = extra_appts * _downstream_to_enrolled(metrics, bench, "appointments")

        findings.append({
            "code": "low_appointments",
            "title": "Baja conversión a citas",
            "type": "primary_bottleneck",
            "funnel_zone": "Admisión",
            "affected_stage": "appointments",
            "affected_transition": "contactados → citas",
            "severity_score": round(sev_score, 1),
            "severity_label": "Alta" if sev_score >= 65 else "Media",
            "confidence_score": round(conf_score, 1),
            "confidence_label": "Alta" if conf_score >= 65 else "Media",
            "summary": (
                f"De los contactados, solo {appt_rate_c*100:.0f}% llega a una cita. "
                "La conversación inicial no está llevando al siguiente paso."
            ),
            "rationale": (
                "Pocos contactados agendan cita. Suele indicar propuesta de valor difusa, "
                "fricción para agendar (muchos pasos, sin agenda en línea) o falta de "
                "seguimiento estructurado después del primer contacto."
            ),
            "evidence": [
                f"Citas / contactados: {appt_rate_c*100:.1f}%",
                f"Benchmark SuperLeads: {bench['appointment_rate_contacted']*100:.0f}%",
            ],
            "missing_data": "Razón principal por la que los contactados no agendan",
            "root_cause": "fragmented_channels",
            "solutions": _map_solutions(solutions, "fragmented_channels", rules),
            **_impact(extra_enrolled, metrics),
        })

    # ═══ F. No-show alto en citas ═════════════════════════════════════════
    att_rate = metrics.get("attendance_rate")
    if att_rate is not None and att_rate < thresholds["low_attendance_rate"]:
        no_show = 1 - att_rate
        sev_score = min(85, 50 + no_show * 60)
        conf_score = 72.0 if _q("attended") in ("exact", "approximate") else 55.0

        recovered_att = (appointments or 0) * (bench["attendance_rate"] - att_rate)
        extra_enrolled = recovered_att * _downstream_to_enrolled(metrics, bench, "attended")

        findings.append({
            "code": "high_no_show",
            "title": "Demasiadas citas que no llegan",
            "type": "primary_bottleneck",
            "funnel_zone": "Admisión",
            "affected_stage": "attended",
            "affected_transition": "citas → asistentes",
            "severity_score": round(sev_score, 1),
            "severity_label": "Alta" if sev_score >= 65 else "Media",
            "confidence_score": round(conf_score, 1),
            "confidence_label": "Alta" if conf_score >= 65 else "Media",
            "summary": (
                f"{no_show*100:.0f}% de las citas agendadas no se presenta. "
                "Cada no-show es un prospecto que ya había dicho que sí — y se perdió en el camino."
            ),
            "rationale": (
                "El no-show alto casi siempre se corrige con confirmaciones automáticas "
                "(24h y 2h antes), recordatorios por WhatsApp y reagendamiento inmediato "
                "del que no llegó. Es de las fugas más fáciles de recuperar."
            ),
            "evidence": [
                f"Asistencia a citas: {att_rate*100:.1f}%",
                f"Benchmark saludable: {thresholds['low_attendance_rate']*100:.0f}%+",
            ],
            "missing_data": "Proceso actual de confirmación de citas",
            "root_cause": "high_no_show",
            "solutions": _map_solutions(solutions, "high_no_show", rules),
            **_impact(extra_enrolled, metrics),
        })

    # ═══ G. Bajo cierre en cita ═══════════════════════════════════════════
    close_rate = metrics.get("close_rate_attended")
    if close_rate is not None and close_rate < thresholds["low_close_rate_on_attended"]:
        sev_score = min(90, 55 + (thresholds["low_close_rate_on_attended"] - close_rate) * 150)
        conf_score = 75.0 if _q("enrolled") in ("exact", "approximate") else 50.0

        extra_enrolled = (attended or 0) * (bench["close_rate_attended"] - close_rate)

        findings.append({
            "code": "low_closing",
            "title": "Baja tasa de cierre en la cita",
            "type": "primary_bottleneck",
            "funnel_zone": "Inscripción",
            "affected_stage": "enrolled",
            "affected_transition": "asistentes → inscritos",
            "severity_score": round(sev_score, 1),
            "severity_label": "Alta" if sev_score >= 65 else "Media",
            "confidence_score": round(conf_score, 1),
            "confidence_label": "Alta" if conf_score >= 65 else "Media",
            "summary": (
                f"Solo {close_rate*100:.0f}% de quienes asisten a la cita se inscribe. "
                "El prospecto más caro de conseguir se está perdiendo en el último metro."
            ),
            "rationale": (
                "Los prospectos llegan a la cita pero no inscriben: manejo débil de objeciones, "
                "discurso sin estructura de cierre, o fricción post-cita (trámites, documentos, "
                "falta de seguimiento al indeciso)."
            ),
            "evidence": [
                f"Cierre sobre asistentes: {close_rate*100:.1f}%",
                f"Benchmark SuperLeads: {bench['close_rate_attended']*100:.0f}%",
            ],
            "missing_data": "Guión de cierre actual y manejo de las objeciones principales",
            "root_cause": "weak_closing",
            "solutions": _map_solutions(solutions, "weak_closing", rules),
            **_impact(extra_enrolled, metrics),
        })

    # ═══ H. Proceso con fricción ══════════════════════════════════════════
    steps_heavy = answers.get("admission_steps_count") in ("5_6", "7_mas")
    docs_heavy = answers.get("required_documents_count") in ("6_8", "9_mas")
    resolution_slow = answers.get("days_first_contact_to_resolution") in ("mas_mes",)
    friction_points = sum([steps_heavy, docs_heavy, resolution_slow])
    if friction_points >= 2:
        findings.append({
            "code": "process_friction",
            "title": "Proceso de inscripción con demasiada fricción",
            "type": "primary_bottleneck",
            "funnel_zone": "Inscripción",
            "affected_stage": "enrolled",
            "affected_transition": "asistentes → inscritos",
            "severity_score": 66.0 + friction_points * 4,
            "severity_label": "Alta",
            "confidence_score": 72.0,
            "confidence_label": "Alta",
            "summary": (
                "El proceso pide demasiado: "
                + ", ".join(filter(None, [
                    "5+ pasos para inscribirse" if steps_heavy else None,
                    "6+ documentos" if docs_heavy else None,
                    "más de un mes para resolver" if resolution_slow else None,
                ]))
                + ". Cada paso extra es una oportunidad de abandono."
            ),
            "rationale": (
                "La familia decidió inscribirse — y el proceso la hace dudar. Digitalizar pasos, "
                "permitir avance en línea y reducir documentos al mínimo legal recupera "
                "inscripciones que hoy se pierden por cansancio, no por convicción."
            ),
            "evidence": [
                f"Pasos: {answers.get('admission_steps_count','—').replace('_','–')}",
                f"Documentos: {answers.get('required_documents_count','—').replace('_','–')}",
                f"Tiempo a resolución: {answers.get('days_first_contact_to_resolution','—').replace('_',' ')}",
            ],
            "missing_data": "Mapa del proceso actual paso a paso",
            "root_cause": "process_friction",
            "solutions": _map_solutions(solutions, "process_friction", rules),
        })

    # ═══ I. Calidad de leads baja ═════════════════════════════════════════
    if answers.get("lead_quality_perception") == "baja":
        findings.append({
            "code": "low_lead_quality",
            "title": "Leads de baja calidad",
            "type": "supporting_signal",
            "funnel_zone": "Atracción",
            "affected_stage": "leads",
            "affected_transition": "mercado → leads",
            "severity_score": 60.0,
            "severity_label": "Media",
            "confidence_score": 55.0,
            "confidence_label": "Media",
            "summary": (
                "El equipo percibe que la mayoría de los leads no tiene perfil. Eso encarece "
                "todo el embudo: el equipo gasta tiempo en quien nunca iba a inscribirse."
            ),
            "rationale": (
                "Leads sin perfil suelen venir de segmentación amplia o mensajes genéricos en "
                "campañas. Calificar en la entrada (formularios y bots con preguntas filtro) y "
                "ajustar la segmentación sube la calidad sin subir el presupuesto."
            ),
            "evidence": ["Percepción del equipo: calidad baja", f"Mejor fuente actual: {answers.get('best_enrollments_source','—')}"],
            "missing_data": "Tasa de calificación por canal de origen",
            "root_cause": "low_lead_quality",
            "solutions": _map_solutions(solutions, "low_lead_quality", rules),
        })

    # ═══ J. Sin estructura digital ════════════════════════════════════════
    crm = answers.get("uses_crm", "")
    channels_integrated = answers.get("channels_integrated", "")
    has_dashboard = answers.get("has_stage_dashboard", "")

    # Requiere que el usuario haya respondido las preguntas de estructura
    # (al menos CRM y dashboard) — no se infiere con formulario vacío.
    answered_structure = bool(crm) and bool(has_dashboard)
    no_digital = (
        crm == "no" and
        channels_integrated in ("no", "parcial", "") and
        has_dashboard in ("no", "")
    )
    if answered_structure and no_digital and (contact_rate is None or contact_rate < 0.7):
        findings.append({
            "code": "no_digital_structure",
            "title": "Sin estructura digital de admisiones",
            "type": "primary_bottleneck",
            "funnel_zone": "Estructura",
            "affected_stage": "sistema",
            "affected_transition": "proceso completo",
            "severity_score": 72.0,
            "severity_label": "Alta",
            "confidence_score": 68.0,
            "confidence_label": "Media-Alta",
            "summary": "El proceso vive en hojas de cálculo, WhatsApp y correo sin un sistema central que dé trazabilidad.",
            "rationale": (
                "Sin CRM ni dashboard de etapas es imposible saber dónde se rompe el proceso. "
                "La fuga existe pero no se puede medir ni corregir — todo lo demás que detecte "
                "este diagnóstico será difícil de mejorar sin esta base."
            ),
            "evidence": ["Sin CRM confirmado", "Canales no integrados", "Sin dashboard de etapas"],
            "missing_data": "Detalle del proceso actual de seguimiento",
            "root_cause": "no_digital_structure",
            "solutions": _map_solutions(solutions, "no_digital_structure", rules),
        })

    # ═══ Fallback preliminar ══════════════════════════════════════════════
    if not findings and (leads is not None or enrolled is not None):
        enroll_rate = metrics.get("enroll_rate")
        findings.append({
            "code": "preliminary_conversion",
            "title": "Conversión global por debajo del potencial",
            "type": "supporting_signal",
            "funnel_zone": "Embudo completo",
            "affected_stage": "enrolled",
            "affected_transition": "leads → inscritos",
            "severity_score": 55.0,
            "severity_label": "Media",
            "confidence_score": 45.0,
            "confidence_label": "Preliminar",
            "summary": f"Con los datos disponibles, la conversión global es de {enroll_rate*100:.1f}%." if enroll_rate else "Se necesitan más datos para un diagnóstico preciso.",
            "rationale": "Diagnóstico preliminar basado en datos parciales. Para mayor certeza se requieren más etapas del embudo.",
            "evidence": [f"Leads: {leads:,}" if leads else "Sin dato de leads", f"Inscritos: {enrolled:,}" if enrolled else "Sin dato de inscritos"],
            "missing_data": "Contactados, citas y asistentes para diagnóstico completo",
            "root_cause": "low_conversion",
            "solutions": _map_solutions(solutions, "low_conversion", rules),
        })

    # ═══ Priorización ═════════════════════════════════════════════════════
    # severity (35%) + cercanía al dinero (25%) + confianza (20%) + impacto económico (20%)
    money_proximity_map = {
        "low_closing": 0.95, "high_no_show": 0.90, "low_appointments": 0.80,
        "slow_first_response": 0.75, "low_contactation": 0.70,
        "after_hours_leak": 0.70, "process_friction": 0.65,
        "low_volume": 0.60, "low_lead_quality": 0.55,
        "no_digital_structure": 0.50, "preliminary_conversion": 0.40,
    }
    max_money = max((f.get("impact_money", 0) for f in findings), default=0)
    for f in findings:
        mp = money_proximity_map.get(f["code"], 0.5)
        impact_norm = (f.get("impact_money", 0) / max_money) if max_money else 0
        f["priority_score"] = round(
            f["severity_score"] * 0.35 +
            mp * 100 * 0.25 +
            f["confidence_score"] * 0.20 +
            impact_norm * 100 * 0.20,
            1
        )

    findings.sort(key=lambda x: x["priority_score"], reverse=True)
    top = findings[:4]

    # ═══ Certeza global ═══════════════════════════════════════════════════
    if top:
        certainty = sum(f["confidence_score"] for f in top) / len(top)
    else:
        certainty = 0.0
    if is_preliminary:
        certainty *= 0.7

    # ═══ Total recuperable — embudo ideal vs. actual (SIN doble conteo) ════
    # En vez de sumar el impacto de cada hallazgo (que se solapan porque atacan
    # el mismo embudo), recalculamos el embudo llevando cada métrica AL MENOS al
    # benchmark y comparamos los inscritos resultantes con los actuales.
    # Esto es matemáticamente limpio y defendible: nunca sobreestima.
    total_recoverable = _compute_total_recoverable(metrics, bench)

    return {
        "findings": top,
        "metrics": metrics,
        "completeness_score": round(completeness, 1),
        "certainty_score": round(certainty, 1),
        "is_preliminary": is_preliminary,
        "total_findings_detected": len(findings),
        "total_recoverable": total_recoverable,
    }


def _map_solutions(solutions: dict, root_cause: str, rules: dict) -> list:
    mapping = rules.get("solution_mapping_by_root_cause", {}).get(root_cause, {})
    result = []
    for role, sol_id in mapping.items():
        if sol_id in solutions:
            s = solutions[sol_id]
            result.append({
                "id": sol_id,
                "name": s["name"],
                "role": role,
                "public_message": s["public_message"],
                "internal_message": s.get("internal_message", ""),
                "demo_angle": s.get("demo_angle", ""),
            })
    return result
