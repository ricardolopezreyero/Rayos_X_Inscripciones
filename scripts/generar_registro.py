"""
generar_registro.py — Genera registro.csv con todos los datos de diagnóstico.
Pensado para que vendedores lleguen preparados a visitar instituciones.

Uso: python3 scripts/generar_registro.py
"""
import sqlite3, json, os, csv, sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB       = os.path.join(BASE, "rayosx.db")
CSV_PATH = os.path.join(BASE, "archivo", "registro.csv")
PDF_DIR  = os.path.join(BASE, "static", "pdfs")
ARCHIVO  = os.path.join(BASE, "archivo")

def yn(v):
    s = str(v).lower() if v else ''
    if s in ('si','yes','sí','true','1'): return 'Sí'
    if s in ('no','false','0'):            return 'No'
    if s == 'parcial':                     return 'Parcial'
    if s == 'informal':                    return 'Informal'
    return str(v) if v else ''

def pct(v):
    return f"{int(v)}%" if v else ''

def num(v):
    try: return f"{int(v):,}"
    except: return str(v) if v else ''

def money(v):
    try: return f"${int(v):,}"
    except: return str(v) if v else ''

def fix_str(s):
    if not s: return ''
    try:   return s.encode('latin-1').decode('utf-8')
    except: return s

CHANNEL_LABELS = {
    'ch_1':'Facebook Ads','ch_2':'Instagram','ch_3':'Google Ads',
    'ch_4':'TikTok','ch_5':'WhatsApp orgánico','ch_6':'Referidos',
    'ch_7':'Sitio web','ch_8':'Visitas presenciales','ch_9':'Ferias',
}
LOSS_MAP = {
    'precio':'Precio alto',
    'competencia':'Se fue con la competencia',
    'desinteres':'Perdió interés',
    'sin_respuesta':'No respondió al seguimiento',
    'documentos':'Problema con documentos',
    'falta_seguimiento':'Falta de seguimiento',
    'no_convencio':'No se convenció del valor',
    'distancia':'Distancia / logística',
}
VEL_MAP = {
    'inmediato':'Inmediato (< 1 hora)',
    'horas':'Mismo día',
    'dia':'Al día siguiente',
    'dias':'2–3 días',
    'no_medimos':'No lo miden ⚠️',
}
DIAS_MAP = {
    'menos_semana':'< 1 semana',
    'una_dos_semanas':'1–2 semanas',
    'mes':'Aprox. 1 mes',
    'mas_mes':'Más de 1 mes ⚠️',
}
HOR_MAP = {
    'horario_oficina':'Solo horario de oficina',
    'extendido':'Horario extendido',
    '24_7':'24/7',
}
COB_MAP = {
    'si':'Sí, cubierto',
    'no':'Sin cobertura ⚠️',
    'parcial':'Parcial',
}
CAL_MAP = {
    'alta':'Alta ✓',
    'media':'Media',
    'baja':'Baja ⚠️',
}

HEADERS = [
    # ── Identificación ─────────────────────────────────────────────────────────
    'Código','Estado','Fecha diagnóstico',
    # ── Datos de contacto ──────────────────────────────────────────────────────
    'Institución','Tipo','Ciudad',
    'Nombre contacto','Email','Teléfono','Sitio web',
    # ── Tamaño y potencial económico ───────────────────────────────────────────
    'Alumnos actuales','Capacidad máxima','Cupo disponible',
    'Colegiatura promedio','Meta inscripciones nuevas',
    'Modalidad','Conversaciones por día',
    # ── Embudo actual (dónde se pierde) ────────────────────────────────────────
    'Leads anuales (est.)','% Contactación','% Citas',
    '% Asistencia a cita','% Cierre','Inscripciones reales',
    'Mejor fuente de inscripciones',
    # ── Problemas detectados ───────────────────────────────────────────────────
    'Principal razón de pérdida','Calidad percibida de leads',
    'Velocidad de primer contacto','Tiempo en resolver un lead',
    'Objeciones que más escuchan',
    # ── Gaps (herramientas que NO tienen = oportunidades) ──────────────────────
    'Usa CRM','Usa Excel / hojas de cálculo',
    'Tiene scripts de seguimiento','Conversaciones centralizadas',
    'Tiene dashboard de etapas','Usa IA conversacional',
    'Seguimiento automatizado','Horario de atención a leads',
    'Cobertura fuera de horario','Canales de marketing activos',
    # ── Lo que dijeron con sus propias palabras ────────────────────────────────
    'Sus notas del diagnóstico',
    'Notas internas del asesor',
    'Competidores que mencionaron',
    'Siguiente paso acordado',
    # ── Resultado del diagnóstico ──────────────────────────────────────────────
    'Score certeza diagnóstico','PDF disponible','Asesor SuperLeads',
]

def generar():
    os.makedirs(ARCHIVO, exist_ok=True)
    conn = sqlite3.connect(DB)
    rows = conn.execute("""
        SELECT short_code, status, started_at, analyzed_at,
               completeness_score, certainty_score, answers_json,
               pdf_client_path, pdf_internal_path
        FROM sessions ORDER BY started_at DESC
    """).fetchall()

    with open(CSV_PATH, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(HEADERS)
        for row in rows:
            code, status, started, analyzed, comp, cert, answers_raw, cli_path, int_path = row
            a = json.loads(answers_raw or '{}')

            canales = [lbl for key, lbl in CHANNEL_LABELS.items() if a.get(key)]
            objeciones = ' / '.join(filter(None,[
                a.get('obj_1'),a.get('obj_3'),a.get('obj_4'),a.get('obj_7'),
                a.get('top_2_objections_text')
            ]))
            try:
                cupo = int(a.get('max_capacity') or 0) - int(a.get('current_enrollment') or 0)
                cupo_str = num(cupo) if cupo > 0 else '—'
            except: cupo_str = ''

            cli_ok = bool(cli_path and os.path.exists(cli_path)) or \
                     os.path.exists(os.path.join(PDF_DIR, f"rayosx_cliente_{code}.pdf"))

            writer.writerow([
                code,
                'Analizado ✓' if status=='analyzed' else 'En progreso',
                str(analyzed or started or '')[:10],

                fix_str(a.get('institution_name','')),
                a.get('institution_type',''),
                fix_str(a.get('city','')),
                fix_str(a.get('contact_name','')),
                a.get('contact_email',''),
                a.get('contact_phone',''),
                a.get('website_url',''),

                num(a.get('current_enrollment')),
                num(a.get('max_capacity')),
                cupo_str,
                money(a.get('average_ticket')),
                num(a.get('target_new_enrollments')),
                a.get('main_modality',''),
                num(a.get('daily_conversations')),

                num(a.get('leads')),
                pct(a.get('contact_pct')),
                pct(a.get('appointment_pct')),
                pct(a.get('attendance_pct')),
                pct(a.get('close_pct')),
                num(a.get('enrolled')),
                a.get('best_enrollments_source',''),

                LOSS_MAP.get(a.get('primary_loss_reason',''), a.get('primary_loss_reason','')),
                CAL_MAP.get(a.get('lead_quality_perception',''), a.get('lead_quality_perception','')),
                VEL_MAP.get(a.get('first_contact_delay_bucket',''), a.get('first_contact_delay_bucket','')),
                DIAS_MAP.get(a.get('days_first_contact_to_resolution',''), a.get('days_first_contact_to_resolution','')),
                fix_str(objeciones),

                yn(a.get('uses_crm')),
                yn(a.get('uses_spreadsheets')),
                yn(a.get('has_followup_scripts')),
                yn(a.get('conversations_centralized')),
                yn(a.get('has_stage_dashboard')),
                yn(a.get('uses_conversational_ai')),
                yn(a.get('automated_followup')),
                HOR_MAP.get(a.get('lead_attention_schedule',''), a.get('lead_attention_schedule','')),
                COB_MAP.get(a.get('after_hours_coverage',''), a.get('after_hours_coverage','')),
                ', '.join(canales),

                fix_str(a.get('initial_notes','')),
                fix_str(a.get('internal_notes','')),
                fix_str(a.get('main_competitors','')),
                fix_str(a.get('next_step','')),

                f"{cert:.0f}%" if cert else '',
                'Sí' if cli_ok else '',
                fix_str(a.get('operator_name','')),
            ])

    conn.close()
    print(f"registro.csv actualizado: {len(rows)} sesiones, {len(HEADERS)} columnas")
    return len(rows)

if __name__ == "__main__":
    generar()
