# Rayos X Conversacional SuperLeads

MVP estático para diagnosticar el sistema de inscripciones de una institución educativa y detectar el cuello de botella más probable del proceso comercial.

La app guía al usuario paso a paso, reconstruye el embudo real, identifica hasta 3 hallazgos priorizados, separa cuello principal de causa raíz y recomienda los productos exactos de SuperLeads.

## Descripción corta del repositorio

Radiografía conversacional del sistema de inscripciones para instituciones educativas. Detecta cuellos de botella, explica causa raíz y genera un reporte comercial premium con recomendaciones de SuperLeads.

## Qué hace

- Hace preguntas por etapas.
- Guarda todo automáticamente en `localStorage`.
- Reconstruye el embudo de admisiones.
- Calcula métricas determinísticas.
- Detecta el cuello principal y hasta 2 secundarios.
- Genera un reporte visual.
- Prepara un PDF premium para guardar o imprimir.
- Tiene fallback de reporte con `jsPDF` si la ruta premium falla.

## Stack

- `index.html`
- `style.css`
- `app.js`
- `localStorage`
- `jsPDF` por CDN
- `Paged.js` por CDN para la versión editorial del PDF

Sin framework.  
Sin backend.  
Sin base de datos.  
Sin build.

## Estructura

```text
Rayos X Conversacional/
├── index.html
├── style.css
├── app.js
└── README.md
```

## Cómo abrirlo

### Opción 1: abrir el archivo directo

Abre:

```text
index.html
```

### Opción 2: correr servidor local

Desde la carpeta del proyecto:

```bash
cd "Rayos X Conversacional"
python3 -m http.server 8080
```

Luego abre:

```text
http://localhost:8080
```

## Cómo compartirlo con alguien fuera de tu red

### Opción rápida: Cloudflare Tunnel

En una terminal:

```bash
cd "Rayos X Conversacional"
python3 -m http.server 8080
```

En otra terminal:

```bash
cloudflared tunnel --url http://localhost:8080
```

### Opción estable: hosting estático

Puedes subir esta carpeta a:

- Netlify
- Vercel
- GitHub Pages

## Lógica del diagnóstico

La decisión no usa IA.  
El diagnóstico es determinístico y parte de las respuestas del usuario.

Calcula al menos:

- `lead_to_contact_rate`
- `lead_to_appointment_rate`
- `contacted_to_appointment_rate`
- `appointment_to_attended_rate`
- `attended_to_enrolled_rate`
- `lead_to_enrolled_rate`

También calcula:

- suficiencia de leads
- capacidad disponible
- desorden estructural
- calidad del dato
- confianza del hallazgo
- costo de oportunidad

## Cuellos principales posibles

- Falta de prospectos
- Baja conversión de lead a inscrito
- Baja cantidad de citas
- Baja tasa de cierre en la cita
- Falta de estructura digital de admisiones
- Hallazgo estructural

## Flujo del usuario

1. Inicia el diagnóstico.
2. Captura URL y datos básicos.
3. Responde preguntas por bloques.
4. Ve resultados visuales.
5. Ajusta el embudo si hace falta.
6. Prepara el PDF premium.
7. Puede borrar la sesión y volver a empezar.

## Guardado de sesión

La app guarda en `localStorage`:

- datos básicos
- respuestas
- métricas
- resultado del diagnóstico
- timestamps

## PDF

El reporte incluye:

- datos básicos
- sello de emisión CDMX
- resumen ejecutivo
- embudo visual
- hallazgos priorizados
- costo de no hacer nada
- preguntas y respuestas
- productos recomendados
- cierre con Constanza

## Notas importantes

- El botón de PDF prepara un reporte premium pensado para guardar como PDF desde el navegador.
- Si esa ruta falla, existe fallback técnico con `jsPDF`.
- Los productos recomendados están limitados a máximo 3.
- El proyecto está optimizado para desktop y móvil.
- El proyecto puede publicarse fácilmente en GitHub Pages, Netlify o Vercel por ser completamente estático.

## Archivos principales

- `index.html`
- `style.css`
- `app.js`

## Sugerencia para GitHub

Si vas a crear el repositorio público, te conviene usar algo así:

- Nombre: `Rayos_X_Conversacional`
- Descripción: `Radiografía conversacional del sistema de inscripciones con diagnóstico determinístico y reporte premium en PDF.`

Si quieres publicarlo rápido, GitHub Pages también funciona bien para este proyecto.
