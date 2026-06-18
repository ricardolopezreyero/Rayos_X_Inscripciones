# Rayos X Inscripciones — SuperLeads

> Diagnóstico guiado para detectar exactamente dónde se rompe el sistema de inscripciones de una institución educativa.

**URL pública:** [rayosx.superleads.mx](https://rayosx.superleads.mx)

---

## ¿Qué es?

Rayos X Inscripciones es una herramienta web de diagnóstico en 5 pasos (~10 min) que permite a una institución educativa identificar con precisión los problemas en su proceso de captación y conversión de alumnos.

Al terminar genera:
- Un **PDF para el director** con los hallazgos y recomendaciones visuales
- Un **PDF interno** para el asesor SuperLeads con datos de seguimiento
- Un **registro en CSV** con todos los datos del diagnóstico, listo para el equipo de ventas

### Pasos del diagnóstico

| Paso | Tema | Datos clave |
|------|------|-------------|
| 1 | Identidad de la institución | Nombre, tipo, ciudad, contacto, URL |
| 2 | Números del embudo | Leads, contactación, citas, asistencia, cierre |
| 3 | Velocidad y contactación | Tiempo de respuesta, horarios, seguimiento |
| 4 | Canales y estructura | Canales activos, CRM, centralización |
| 5 | Calidad y mercado | Percepción de leads, competidores, objeciones |

---

## Arquitectura

```
Internet → Cloudflare CDN + Worker → Cloudflare Tunnel (QUIC)
                                              ↓
                                    uvicorn [::]:8765 (Mac local)
                                              ↓
                                    FastAPI + SQLite + ReportLab
```

### Stack técnico

| Componente | Tecnología |
|---|---|
| Backend | Python 3.14 + FastAPI + Starlette |
| Base de datos | SQLite con WAL mode |
| PDFs | ReportLab |
| Templates | Jinja2 |
| Infraestructura | Cloudflare Tunnel + macOS LaunchAgents |
| Dominio | `rayosx.superleads.mx` vía Cloudflare DNS |

---

## Estructura del proyecto

```
rayosx/
├── app/
│   ├── main.py                  # Rutas FastAPI (landing, pasos, análisis, PDFs)
│   ├── database.py              # SQLAlchemy + SQLite WAL mode
│   ├── capitaltorreon.py        # Dashboard CapitalTorreon (router separado)
│   └── services/
│       ├── diagnosis_engine.py  # Motor de análisis — genera findings
│       └── pdf_service.py       # Generación de PDFs cliente e interno
│
├── templates/rayosx/
│   ├── base.html                # Layout base + CSS dark theme
│   ├── landing.html             # Página de inicio + recuperar sesión
│   ├── step_identity.html       # Paso 1 — Identidad
│   ├── step_funnel.html         # Paso 2 — Embudo
│   ├── step_velocity.html       # Paso 3 — Velocidad
│   ├── step_channels.html       # Paso 4 — Canales
│   ├── step_market.html         # Paso 5 — Mercado
│   ├── review.html              # Revisión antes de analizar
│   ├── analyzing.html           # Animación de análisis
│   └── results.html             # Resultados + descarga PDFs
│
├── static/
│   ├── pdfs/                    # PDFs temporales para descarga (60 días)
│   └── img/                     # Imágenes estáticas
│
├── scripts/
│   ├── watchdog.sh              # Verifica y repara servicios cada 5 min
│   ├── backup_db.sh             # Backup diario de la DB con integridad check
│   ├── generar_registro.py      # Genera registro.csv con datos de ventas
│   ├── cleanup_pdfs.sh          # Limpia PDFs > 60 días
│   ├── wake_recovery.sh         # Reconexión post-sleep de la Mac
│   └── status.sh                # Diagnóstico rápido del sistema
│
├── cloudflared/
│   ├── config.yml               # Configuración local del tunnel Cloudflare
│   └── worker_maintenance.js    # Worker CF: página de mantenimiento en 502/503
│
├── requirements.txt             # Dependencias Python fijadas
└── README.md                    # Este archivo
```

---

## Base de datos

Tabla principal: `sessions`

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID | Identificador único de sesión |
| `short_code` | String | Código de 8 caracteres para recuperar sesión |
| `status` | String | `in_progress` / `analyzed` |
| `answers_json` | Text | Respuestas completas del diagnóstico (JSON) |
| `findings_json` | Text | Hallazgos generados por el motor de análisis |
| `completeness_score` | Float | Puntaje de completitud (0–100) |
| `certainty_score` | Float | Puntaje de certeza del diagnóstico (0–100) |
| `pdf_client_path` | String | Ruta al PDF del cliente |
| `pdf_internal_path` | String | Ruta al PDF interno |

**Configuración:** WAL mode + cache 32MB + mmap 128MB para máxima estabilidad en producción.

---

## Rutas principales

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Landing page |
| `POST` | `/start` | Crear nueva sesión |
| `POST` | `/recuperar` | Recuperar sesión por código |
| `GET/POST` | `/paso/{1-5}/{id}` | Pasos del diagnóstico |
| `GET` | `/revision/{id}` | Revisión antes de analizar |
| `POST` | `/analizar/{id}` | Iniciar análisis |
| `GET` | `/analizando/{id}` | Página de animación |
| `GET` | `/run-analysis/{id}` | Ejecutar análisis (llamado por JS) |
| `GET` | `/resultados/{id}` | Página de resultados |
| `GET` | `/pdf/cliente/{id}` | Descargar PDF del cliente |
| `GET` | `/pdf/interno/{id}` | Descargar PDF interno |
| `GET` | `/healthz` | Health check (verifica DB + devuelve stats) |

---

## Infraestructura — LaunchAgents macOS

El sistema corre en una Mac local expuesta vía Cloudflare Tunnel. Todos los servicios se auto-reinician con LaunchAgents:

| Label | Descripción | Frecuencia |
|---|---|---|
| `mx.superleads.rayosx-app` | Uvicorn (app Python) en `[::]:8765` | On crash |
| `mx.superleads.rayosx-tunnel` | Cloudflare Tunnel | On crash |
| `mx.superleads.rayosx-watchdog` | Verifica HTTP + repara cadena completa | Cada 5 min |
| `mx.superleads.rayosx-backup` | Backup DB + actualiza `registro.csv` | 3 AM diario |
| `mx.superleads.rayosx-cleanup` | Limpia PDFs > 60 días | Lunes 3 AM |
| `mx.superleads.rayosx-wake` | Reconecta servicios tras sleep/wake de Mac | En cada wake |

---

## Cloudflare

| Componente | Configuración |
|---|---|
| Tunnel | `cc8f8373-badb-4e96-a419-5bd6e3075620` → `http://127.0.0.1:8765` |
| Worker | `rayosx-gateway` — intercepta 502/503 y muestra página de mantenimiento |
| Ruta Worker | `rayosx.superleads.mx/*` |
| DNS | CNAME `rayosx` → tunnel UUID en `superleads.mx` |

---

## Registro y archivo de sesiones

Cada diagnóstico completado genera:
1. PDFs en `static/pdfs/` (disponibles para descarga 60 días)
2. Copia permanente en `archivo/YYYY-MM/FECHA_CODIGO_Institución/`
3. Entrada en `archivo/registro.csv` (actualizado diariamente)

El `registro.csv` contiene **46 columnas** con todos los datos del diagnóstico organizados para el equipo de ventas:
- Datos de contacto completos
- Tamaño de la institución y potencial económico
- Métricas del embudo de inscripciones
- Problemas detectados con sus indicadores de urgencia
- Herramientas que no tienen (gaps = oportunidades)
- Lo que dijeron con sus propias palabras

---

## Instalación local

```bash
# 1. Clonar
git clone https://github.com/ricardolopezreyero/Rayos_X_Inscripciones.git
cd Rayos_X_Inscripciones

# 2. Instalar dependencias
pip3 install -r requirements.txt

# 3. Iniciar
python3 -m uvicorn app.main:app --host :: --port 8765

# 4. Abrir
open http://localhost:8765
```

---

## Diagnóstico del sistema (producción)

```bash
bash scripts/status.sh
```

Muestra en tiempo real el estado de uvicorn, tunnel, LaunchAgents y conectividad HTTP.

---

## Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `RAYOSX_PIN` | — | (Eliminado — acceso libre sin PIN) |

---

## Historial de versiones

| Versión | Fecha | Cambios principales |
|---|---|---|
| V8 MVP | May 2026 | Versión inicial publicada |
| V8.1 | Jun 2026 | Fix IPv6 dual-stack, Worker CF, backups, registro CSV ventas |
| V9 | Jun 2026 | Embudo en cascada, multi-selección, números en vivo, motor con 10 hallazgos |
| V10 | Jun 2026 | Auditoría de fórmulas (8,640 escenarios), total recuperable sin doble conteo, tasas acotadas, arquitectura simplificada (sin proxy) |

---

*SuperLeads · Sistema de Inscripciones Educativas · [superleads.mx](https://superleads.mx)*
