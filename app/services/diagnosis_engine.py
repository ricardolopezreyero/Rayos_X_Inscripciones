"""Deterministic diagnosis engine — no LLM required for core logic."""
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


def _quality_weight(quality: str) -> float:
    w = {"exact": 1.0, "approximate": 0.72, "unknown": 0.0}
    return w.get(quality, 0.5)


def _parse_int(v) -> Optional[int]:
    try:
        return int(v) if v not in (None, "", "no_se") else None
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

    m["contact_rate"] = _safe_div(vals["contacted"], vals["leads"])
    m["appointment_rate_leads"] = _safe_div(vals["appointments"], vals["leads"])
    m["appointment_rate_contacted"] = _safe_div(vals["appointments"], vals["contacted"])
    m["attendance_rate"] = _safe_div(vals["attended"], vals["appointments"])
    m["no_show_rate"] = (1 - m["attendance_rate"]) if m["attendance_rate"] is not None else None
    m["enroll_rate"] = _safe_div(vals["enrolled"], vals["leads"])
    m["close_rate_attended"] = _safe_div(vals["enrolled"], vals["attended"])
    m["close_rate_appointments"] = _safe_div(vals["enrolled"], vals["appointments"])
    m["ctr"] = _safe_div(vals["clicks"], vals["impressions"])

    # Leaks in absolute numbers
    if vals["leads"] and vals["contacted"]:
        m["leak_lead_to_contacted"] = vals["leads"] - vals["contacted"]
    if vals["contacted"] and vals["appointments"]:
        m["leak_contacted_to_appointment"] = vals["contacted"] - vals["appointments"]
    if vals["appointments"] and vals["attended"]:
        m["leak_appointment_to_attended"] = vals["appointments"] - vals["attended"]
    if vals["attended"] and vals["enrolled"]:
        m["leak_attended_to_enrolled"] = vals["attended"] - vals["enrolled"]

    # Average ticket and opportunity
    ticket = _parse_int(answers.get("average_ticket"))
    capacity = _parse_int(answers.get("max_capacity"))
    enrollment = _parse_int(answers.get("current_enrollment"))
    target = _parse_int(answers.get("target_new_enrollments"))

    if capacity and enrollment:
        m["capacity_available"] = capacity - enrollment
    if m.get("capacity_available") and ticket:
        m["opportunity_value"] = m["capacity_available"] * ticket

    if target and vals["enrolled"]:
        m["gap_to_target"] = target - vals["enrolled"]

    m["data_quality"] = {k: quals[k] for k in funnel_keys}
    return m


def _compute_completeness(answers: dict, metrics: dict) -> float:
    """0-100 score based on key fields present."""
    high_value_fields = [
        ("leads", 15), ("enrolled", 15), ("appointments", 10),
        ("first_contact_delay_bucket", 8), ("uses_crm", 7),
        ("channels_integrated", 7), ("top_2_objections", 6),
        ("max_capacity", 5), ("target_new_enrollments", 5),
        ("contacted", 8), ("attended", 5), ("average_ticket", 5),
        ("institution_name", 4),
    ]
    score = 0
    total = sum(w for _, w in high_value_fields)
    for field, weight in high_value_fields:
        v = answers.get(field)
        if v and str(v).strip() not in ("", "no_se", "no_lo_se"):
            score += weight
    return min(100.0, (score / total) * 100)


def _first_response_delay_minutes(bucket: str) -> Optional[int]:
    mapping = {
        "menos_5": 3, "5_15": 10, "15_60": 40,
        "1_3h": 120, "mas_3h": 360, "no_medimos": 500,
    }
    return mapping.get(bucket)


def run_diagnosis(answers: dict) -> dict:
    rules = _load_rules()
    solutions = _load_solutions()["solutions"]
    thresholds = rules["thresholds"]

    metrics = compute_funnel_metrics(answers)
    completeness = _compute_completeness(answers, metrics)
    is_preliminary = completeness < 30

    findings = []

    # --- FINDING A: Falta de prospectos ---
    leads = metrics.get("leads")
    enrolled = metrics.get("enrolled")
    target = metrics.get("gap_to_target") is not None and metrics.get("gap_to_target", 0) > 0
    enroll_rate = metrics.get("enroll_rate")

    if leads is not None and enrolled is not None:
        # If leads are very low relative to target or absolute numbers
        leads_needed = None
        if enroll_rate and enrolled:
            if enroll_rate > 0:
                leads_needed = enrolled / enroll_rate

        gap = metrics.get("gap_to_target", 0) or 0
        capacity = metrics.get("capacity_available", 0) or 0

        low_volume = (
            (leads is not None and leads < 50) or
            (leads is not None and answers.get("target_new_enrollments") and
             _parse_int(answers.get("target_new_enrollments")) and
             leads < _parse_int(answers.get("target_new_enrollments")) * 5)
        )

        if low_volume and capacity > 0:
            sev_score = min(90, 40 + (capacity / max(capacity, leads or 1)) * 30)
            conf_raw = 0.6 if metrics["data_quality"].get("leads") == "exact" else 0.4
            conf_score = conf_raw * 100

            impact = None
            ticket = _parse_int(answers.get("average_ticket"))
            if ticket and capacity:
                impact = min(capacity, gap) * ticket if gap else capacity * ticket * 0.5

            findings.append({
                "code": "low_volume",
                "title": "Volumen insuficiente de prospectos",
                "type": "primary_bottleneck",
                "funnel_zone": "Atracción",
                "affected_stage": "leads",
                "affected_transition": "impressions → leads",
                "severity_score": round(sev_score, 1),
                "severity_label": "Alta" if sev_score >= 65 else "Media",
                "confidence_score": round(conf_score, 1),
                "confidence_label": "Alta" if conf_score >= 65 else "Media",
                "summary": f"Con {leads} leads, el embudo no tiene suficiente volumen para alcanzar la meta de inscritos.",
                "rationale": "El número de prospectos entrantes es insuficiente para que, incluso con una conversión razonable, se alcance el objetivo de inscripción.",
                "evidence": [f"Leads registrados: {leads}", f"Espacio disponible: {capacity} lugares"],
                "missing_data": "Impresiones y alcance para medir eficiencia de captación",
                "estimated_impact": f"${impact:,.0f} en oportunidad no capturada" if impact else None,
                "root_cause": "low_volume",
                "solutions": _map_solutions(solutions, "low_volume", rules),
            })

    # --- FINDING B: Baja contactación ---
    contact_rate = metrics.get("contact_rate")
    if contact_rate is not None and contact_rate < thresholds["low_contact_rate"]:
        delay_bucket = answers.get("first_contact_delay_bucket", "")
        delay_min = _first_response_delay_minutes(delay_bucket)
        slow_response = delay_min and delay_min >= thresholds["slow_first_response_minutes"]

        base_sev = 55 + (thresholds["low_contact_rate"] - contact_rate) * 100
        sev_score = min(92, base_sev)
        conf_base = 0.65
        if metrics["data_quality"].get("contacted") == "exact":
            conf_base = 0.80
        if slow_response:
            conf_base = min(0.90, conf_base + 0.10)
        conf_score = conf_base * 100

        root = "slow_response" if slow_response else "fragmented_channels"
        rationale = (
            f"Solo el {contact_rate*100:.0f}% de los leads son contactados. "
            + (f"Con un tiempo de primera respuesta de '{delay_bucket.replace('_', ' ')}', muchos prospectos enfrían antes del primer contacto." if slow_response else
               "Los leads no están siendo atendidos de forma sistemática.")
        )

        findings.append({
            "code": "low_contactation",
            "title": "Baja tasa de contactación",
            "type": "primary_bottleneck",
            "funnel_zone": "Admisión",
            "affected_stage": "contacted",
            "affected_transition": "leads → contacted",
            "severity_score": round(sev_score, 1),
            "severity_label": "Alta" if sev_score >= 65 else "Media",
            "confidence_score": round(conf_score, 1),
            "confidence_label": "Alta" if conf_score >= 65 else "Media",
            "summary": f"Solo {contact_rate*100:.0f}% de los leads son contactados. La fuga empieza en el primer paso.",
            "rationale": rationale,
            "evidence": [f"Tasa de contactación: {contact_rate*100:.1f}%", f"Benchmark mínimo esperado: {thresholds['low_contact_rate']*100:.0f}%"],
            "missing_data": "Medición de tiempos de respuesta por asesor",
            "estimated_impact": None,
            "root_cause": root,
            "solutions": _map_solutions(solutions, root, rules),
        })

    # --- FINDING C: Baja cantidad de citas ---
    appt_rate = metrics.get("appointment_rate_leads")
    if appt_rate is not None and appt_rate < thresholds["low_appointment_rate_on_leads"]:
        base_sev = 50 + (thresholds["low_appointment_rate_on_leads"] - appt_rate) * 200
        sev_score = min(88, base_sev)
        conf_score = 70.0 if metrics["data_quality"].get("appointments") in ("exact", "approximate") else 50.0

        findings.append({
            "code": "low_appointments",
            "title": "Baja conversión a citas",
            "type": "primary_bottleneck",
            "funnel_zone": "Admisión",
            "affected_stage": "appointments",
            "affected_transition": "contacted → appointments",
            "severity_score": round(sev_score, 1),
            "severity_label": "Alta" if sev_score >= 65 else "Media",
            "confidence_score": round(conf_score, 1),
            "confidence_label": "Alta" if conf_score >= 65 else "Media",
            "summary": f"Solo {appt_rate*100:.1f}% de los leads llegan a una cita. El proceso pierde prospectos antes de la conversación de fondo.",
            "rationale": "Pocos leads convierten a cita. Esto suele indicar propuesta de valor difusa, fricción para agendar o seguimiento insuficiente.",
            "evidence": [f"Tasa de cita sobre leads: {appt_rate*100:.1f}%", f"Mínimo esperado: {thresholds['low_appointment_rate_on_leads']*100:.0f}%"],
            "missing_data": "Razón principal por la que los leads no agendan",
            "estimated_impact": None,
            "root_cause": "fragmented_channels",
            "solutions": _map_solutions(solutions, "fragmented_channels", rules),
        })

    # --- FINDING D: Bajo cierre en cita ---
    close_rate = metrics.get("close_rate_attended")
    if close_rate is not None and close_rate < thresholds["low_close_rate_on_attended"]:
        base_sev = 55 + (thresholds["low_close_rate_on_attended"] - close_rate) * 150
        sev_score = min(90, base_sev)
        conf_score = 75.0 if metrics["data_quality"].get("enrolled") in ("exact", "approximate") else 50.0

        objections = answers.get("top_2_objections", "")
        findings.append({
            "code": "low_closing",
            "title": "Baja tasa de cierre en la cita",
            "type": "primary_bottleneck",
            "funnel_zone": "Inscripción",
            "affected_stage": "enrolled",
            "affected_transition": "attended → enrolled",
            "severity_score": round(sev_score, 1),
            "severity_label": "Alta" if sev_score >= 65 else "Media",
            "confidence_score": round(conf_score, 1),
            "confidence_label": "Alta" if conf_score >= 65 else "Media",
            "summary": f"Solo {close_rate*100:.1f}% de quienes asisten a la cita se inscriben. El problema está en la conversación de cierre.",
            "rationale": "Los prospectos llegan a la cita pero no inscriben. Esto indica manejo débil de objeciones, discurso sin fuerza o fricción post-cita.",
            "evidence": [f"Tasa de cierre sobre asistentes: {close_rate*100:.1f}%", f"Umbral crítico: {thresholds['low_close_rate_on_attended']*100:.0f}%"],
            "missing_data": "Guión de cierre actual y manejo de objeciones principales",
            "estimated_impact": None,
            "root_cause": "weak_closing",
            "solutions": _map_solutions(solutions, "weak_closing", rules),
        })

    # --- FINDING E: Sin estructura digital ---
    crm = answers.get("uses_crm", "")
    spreadsheets = answers.get("uses_spreadsheets", "")
    channels_integrated = answers.get("channels_integrated", "")
    has_dashboard = answers.get("has_stage_dashboard", "")

    no_digital = (
        crm in ("no", "") and
        channels_integrated in ("no", "parcial", "") and
        has_dashboard in ("no", "")
    )
    if no_digital and (contact_rate is None or contact_rate < 0.7):
        sev_score = 72.0
        conf_score = 68.0

        findings.append({
            "code": "no_digital_structure",
            "title": "Sin estructura digital de admisiones",
            "type": "primary_bottleneck",
            "funnel_zone": "Estructura",
            "affected_stage": "sistema",
            "affected_transition": "proceso completo",
            "severity_score": sev_score,
            "severity_label": "Alta",
            "confidence_score": conf_score,
            "confidence_label": "Media-Alta",
            "summary": "El proceso vive en hojas de cálculo, WhatsApp y correo sin un sistema central que dé trazabilidad.",
            "rationale": "Sin CRM ni dashboard de etapas, es imposible detectar dónde se rompe el proceso. La fuga existe pero no se puede medir ni corregir.",
            "evidence": ["Sin CRM confirmado", "Canales no integrados", "Sin dashboard de etapas"],
            "missing_data": "Detalle del proceso actual de seguimiento",
            "estimated_impact": None,
            "root_cause": "no_digital_structure",
            "solutions": _map_solutions(solutions, "no_digital_structure", rules),
        })

    # If no findings from data, add a preliminary one
    if not findings and (leads is not None or enrolled is not None):
        enroll_rate = metrics.get("enroll_rate")
        findings.append({
            "code": "preliminary_conversion",
            "title": "Conversión global por debajo del potencial",
            "type": "supporting_signal",
            "funnel_zone": "Embudo completo",
            "affected_stage": "enrolled",
            "affected_transition": "leads → enrolled",
            "severity_score": 55.0,
            "severity_label": "Media",
            "confidence_score": 45.0,
            "confidence_label": "Preliminar",
            "summary": f"Con los datos disponibles, la conversión global es de {enroll_rate*100:.1f}%" if enroll_rate else "Se necesitan más datos para un diagnóstico preciso.",
            "rationale": "Diagnóstico preliminar basado en datos parciales. Para mayor certeza se requieren más etapas del embudo.",
            "evidence": [f"Leads: {leads}" if leads else "Sin dato de leads", f"Inscritos: {enrolled}" if enrolled else "Sin dato de inscritos"],
            "missing_data": "Contactados, citas y asistentes para diagnóstico completo",
            "estimated_impact": None,
            "root_cause": "low_conversion",
            "solutions": _map_solutions(solutions, "low_conversion", rules),
        })

    # Sort by priority: severity * 0.5 + confidence * 0.3 + money_proximity * 0.2
    money_proximity_map = {
        "low_closing": 0.95, "low_appointments": 0.80,
        "low_contactation": 0.70, "low_volume": 0.60,
        "no_digital_structure": 0.50, "preliminary_conversion": 0.40,
    }
    for f in findings:
        mp = money_proximity_map.get(f["code"], 0.5)
        f["priority_score"] = (
            f["severity_score"] * 0.35 +
            mp * 25 +
            f["confidence_score"] * 0.20
        )

    findings.sort(key=lambda x: x["priority_score"], reverse=True)
    top3 = findings[:3]

    # Compute overall certainty
    if top3:
        certainty = sum(f["confidence_score"] for f in top3) / len(top3)
    else:
        certainty = 0.0

    if is_preliminary:
        certainty *= 0.7

    return {
        "findings": top3,
        "metrics": metrics,
        "completeness_score": round(completeness, 1),
        "certainty_score": round(certainty, 1),
        "is_preliminary": is_preliminary,
        "total_findings_detected": len(findings),
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
