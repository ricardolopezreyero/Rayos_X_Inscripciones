const STORAGE_KEY = "rayos_x_conversacional_superleads_v1";
const NO_SE = "NO_SE";
const DAYS_PER_MONTH = 30.4;
const DAYS_PER_YEAR = 365;
const FX_RATES_TO_MXN = {
  MXN: 1,
  USD: 17,
  COL: 0.0042
};
const SUPERLEADS_LOGO_URL = "https://assets.cdn.filesafe.space/E6Gh1sE1RnPtadmL7wmG/media/68ae10743ba618f9c7da90e0.png";
const CONSTANZA_PHOTO_URL = "https://assets.cdn.filesafe.space/E6Gh1sE1RnPtadmL7wmG/media/69c9492a9dbb4283e9ea6550.png";
const PAGED_JS_POLYFILL_URL = "https://unpkg.com/pagedjs/dist/paged.polyfill.js";
let pdfLogoCache = null;
let pdfLogoPromise = null;
const CONSTANZA_BUTTON_EMOJIS = ["💬", "📲", "📩", "✨", "🟢", "🤝", "🚀", "🧠", "📞", "✅"];
let constanzaEmojiIndex = 0;
let constanzaEmojiInterval = null;
let premiumPrintIframe = null;
const DEFAULT_RECOMMENDED_PRODUCTS = 2;
const MAX_RECOMMENDED_PRODUCTS = 3;
const PRODUCT_CATALOG = [
  {
    name: "Optimización de Puntos de Contacto | Avanzado",
    emoji: "🎯",
    description: "Versión avanzada de optimización digital para ordenar y fortalecer los puntos de entrada más importantes del proceso de admisión, reducir fricción y alinear la presencia digital con el sistema de inscripciones."
  },
  {
    name: "CRM SuperLeads | Básico",
    emoji: "🧩",
    description: "Sistema de gestión de admisiones para ordenar, medir y controlar el proceso comercial de inscripción con implementación inicial, automatizaciones base, paneles de visibilidad, KPIs operativos y soporte."
  },
  {
    name: "CRM SuperLeads | Avanzado",
    emoji: "⚙️",
    description: "Versión avanzada del sistema de gestión de admisiones para instituciones que necesitan una operación más robusta, automatizaciones más sofisticadas y una base más fuerte para escalar inscripciones."
  },
  {
    name: "Dirección Estratégica del Sistema | Avanzado",
    emoji: "🧠",
    description: "Servicio de dirección estratégica con mayor acompañamiento, definición táctica y seguimiento del sistema de inscripciones para alinear decisiones de admisiones con objetivos institucionales y datos reales."
  },
  {
    name: "Campañas Integrales de Generación de Demanda | Básico",
    emoji: "📣",
    description: "Gestión de campañas integrales de captación enfocadas en atraer oportunidades reales, conectarlas con el CRM y optimizar la demanda que sí puede convertirse dentro del sistema."
  },
  {
    name: "Campañas Integrales de Generación de Demanda | Avanzado",
    emoji: "🚀",
    description: "Servicio avanzado de generación de demanda para instituciones que buscan un esfuerzo más robusto de captación, optimización y escalamiento de oportunidades de admisión."
  },
  {
    name: "Content Marketing | Paquete 20 posts",
    emoji: "📝",
    description: "Producción de contenidos alineados a la estrategia definida para apoyar atracción, confianza y conversión dentro del sistema de inscripciones."
  },
  {
    name: "Seguimiento Comercial | Sesión 90 min",
    emoji: "📞",
    description: "Sesión de acompañamiento comercial para mejorar la ejecución diaria del proceso de admisión mediante ajustes de discurso, guiones, objeciones, análisis de conversión y disciplina comercial."
  },
  {
    name: "Taller Inscripción es Cuestión de Ventas | Por participante",
    emoji: "🎓",
    description: "Entrenamiento estructurado para alinear al equipo de admisiones a un enfoque comercial claro y consistente, con manejo de objeciones, seguimiento y adopción del sistema en la operación diaria."
  },
  {
    name: "Dirección Estratégica del Sistema | Básico",
    emoji: "🗺️",
    description: "Acompañamiento estratégico para definir, documentar y dar seguimiento a la dirección del sistema de inscripciones con diagnóstico, revisión de contexto, auditoría del proceso e indicadores clave."
  }
];
const PRODUCT_NAME_SET = new Set(PRODUCT_CATALOG.map((p) => p.name));
const PRODUCT_BY_NAME = PRODUCT_CATALOG.reduce((acc, item) => {
  acc[item.name] = item;
  return acc;
}, {});
const PRODUCT_ALIAS_MAP = {
  "CRM SuperLeads": ["CRM SuperLeads | Básico"],
  "CRM SuperLeads (base operativa)": ["CRM SuperLeads | Básico"],
  "IA Conversacional de SuperLeads": ["CRM SuperLeads | Avanzado"],
  "Optimización de Puntos de Contacto": ["Optimización de Puntos de Contacto | Avanzado"],
  "Seguimiento Comercial": ["Seguimiento Comercial | Sesión 90 min"],
  "Documento Central de Estrategia": ["Dirección Estratégica del Sistema | Básico"],
  "Dirección Estratégica del Sistema de Inscripciones": ["Dirección Estratégica del Sistema | Avanzado"],
  "Sesión de Dirección Estratégica del Sistema de Inscripciones": ["Dirección Estratégica del Sistema | Avanzado"],
  "Campañas Integrales de Generación de Demanda": ["Campañas Integrales de Generación de Demanda | Básico"],
  "Taller \"Inscripción es Cuestión de Ventas\"": ["Taller Inscripción es Cuestión de Ventas | Por participante"],
  "Conversación estratégica con SuperLeads (sin forzar producto estándar)": ["Dirección Estratégica del Sistema | Avanzado"]
};

const state = loadState();
const stages = {
  basic: "Bloque 0 — URL y datos básicos",
  A: "Bloque A — Contexto",
  B: "Bloque B — Embudo real",
  C: "Bloque C — Velocidad y contactación",
  D: "Bloque D — Proceso y estructura",
  E: "Bloque E — Mercado y cierre",
  F: "Bloque F — Capacidad y oportunidad"
};

const yesNoUnknown = [
  { value: "si", label: "Sí" },
  { value: "no", label: "No" },
  { value: NO_SE, label: "No lo sé" }
];

const questions = [
  {
    id: "q1",
    stage: "A",
    type: "multi",
    columns: 3,
    label: "¿Qué niveles educativos ofrecen principalmente?",
    options: [
      { value: "maternal", label: "Maternal" },
      { value: "preescolar", label: "Preescolar" },
      { value: "kinder", label: "Kinder" },
      { value: "primaria_baja", label: "Primaria baja" },
      { value: "primaria_alta", label: "Primaria alta" },
      { value: "secundaria", label: "Secundaria" },
      { value: "bachillerato", label: "Bachillerato" },
      { value: "tecnica", label: "Técnica" },
      { value: "maestria", label: "Maestría" },
      { value: NO_SE, label: "No lo sé" }
    ]
  },
  { id: "q2", stage: "A", type: "textarea", label: "Hoy, antes de ver números, ¿cuál creen que es su mayor cuello de botella en admisiones?" },
  { id: "q3", stage: "A", type: "number", label: "¿Cuántos alumnos tienen hoy?" },
  { id: "q4", stage: "A", type: "number", label: "¿Cuántos nuevos inscritos necesitan para el siguiente ciclo o periodo?" },
  { id: "q5", stage: "A", type: "number", label: "¿Cuál es su capacidad máxima?" },
  { id: "q6", stage: "B", type: "number", label: "En el periodo que vamos a analizar, ¿cuántos leads recibieron aproximadamente?" },
  {
    id: "q7",
    stage: "B",
    type: "single",
    columns: 3,
    autoAdvance: true,
    label: "De esos leads, ¿qué porcentaje sí lograron contactar?",
    options: [
      { value: 0, label: "0%" },
      { value: 10, label: "10%" },
      { value: 20, label: "20%" },
      { value: 30, label: "30%" },
      { value: 40, label: "40%" },
      { value: 50, label: "50%" },
      { value: 60, label: "60%" },
      { value: 70, label: "70%" },
      { value: 80, label: "80%" },
      { value: 90, label: "90%" },
      { value: 100, label: "100%" }
    ]
  },
  {
    id: "q8",
    stage: "B",
    type: "single",
    columns: 3,
    autoAdvance: true,
    label: "¿Qué porcentaje avanzó a cita, visita, recorrido o entrevista?",
    options: [
      { value: 0, label: "0%" },
      { value: 10, label: "10%" },
      { value: 20, label: "20%" },
      { value: 30, label: "30%" },
      { value: 40, label: "40%" },
      { value: 50, label: "50%" },
      { value: 60, label: "60%" },
      { value: 70, label: "70%" },
      { value: 80, label: "80%" },
      { value: 90, label: "90%" },
      { value: 100, label: "100%" }
    ]
  },
  {
    id: "q9",
    stage: "B",
    type: "single",
    columns: 3,
    autoAdvance: true,
    label: "¿Qué porcentaje asistió a esa cita o visita?",
    options: [
      { value: 0, label: "0%" },
      { value: 10, label: "10%" },
      { value: 20, label: "20%" },
      { value: 30, label: "30%" },
      { value: 40, label: "40%" },
      { value: 50, label: "50%" },
      { value: 60, label: "60%" },
      { value: 70, label: "70%" },
      { value: 80, label: "80%" },
      { value: 90, label: "90%" },
      { value: 100, label: "100%" }
    ]
  },
  { id: "q10", stage: "B", type: "number", label: "¿Cuántos terminaron inscritos?" },
  {
    id: "q11",
    stage: "C",
    type: "single",
    label: "Cuando entra un lead nuevo, ¿en cuánto tiempo hacen el primer contacto?",
    options: [
      { value: "menos_5_min", label: "Menos de 5 minutos" },
      { value: "5_30_min", label: "Entre 5 y 30 minutos" },
      { value: "30_120_min", label: "Entre 30 minutos y 2 horas" },
      { value: "mas_2_horas", label: "Más de 2 horas" },
      { value: "mismo_dia", label: "El mismo día" },
      { value: NO_SE, label: "No lo sé" }
    ]
  },
  {
    id: "q12",
    stage: "C",
    type: "single",
    label: "¿Atienden fuera de horario o solo en horario fijo?",
    options: [
      { value: "si_fuera_horario", label: "Sí atendemos fuera de horario" },
      { value: "solo_horario", label: "Solo en horario fijo" },
      { value: NO_SE, label: "No lo sé" }
    ]
  },
  {
    id: "q13",
    stage: "C",
    type: "single",
    label: "¿Usan IA conversacional para responder y calificar leads?",
    options: yesNoUnknown
  },
  {
    id: "q14",
    stage: "C",
    type: "single",
    label: "¿Todas las conversaciones caen en un mismo sistema o están repartidas entre varios canales?",
    options: [
      { value: "unificado", label: "Sistema unificado" },
      { value: "fragmentado", label: "Canales fragmentados" },
      { value: NO_SE, label: "No lo sé" }
    ]
  },
  {
    id: "q15",
    stage: "D",
    type: "single",
    label: "¿Al prospecto le resulta fácil agendar una cita o avanzar en el proceso?",
    options: [
      { value: "facil", label: "Sí, es fácil" },
      { value: "dificil", label: "No, hay fricción" },
      { value: NO_SE, label: "No lo sé" }
    ]
  },
  { id: "q16", stage: "D", type: "single", label: "¿Tienen seguimiento automático?", options: yesNoUnknown },
  { id: "q17", stage: "D", type: "single", label: "¿Usan CRM para admisiones?", options: yesNoUnknown },
  {
    id: "q18",
    stage: "D",
    type: "single",
    label: "¿Hoy operan con hojas de cálculo, WhatsApp, correo y llamadas por separado?",
    options: yesNoUnknown
  },
  { id: "q19", stage: "D", type: "single", label: "¿Tienen un tablero por etapa del embudo?", options: yesNoUnknown },
  {
    id: "q20",
    stage: "E",
    type: "multi",
    columns: 3,
    label: "Cuando pierden un prospecto, ¿normalmente lo pierden más por qué?",
    options: [
      { value: "precio", label: "Precio" },
      { value: "ubicacion", label: "Distancia o ubicación" },
      { value: "reputacion", label: "Reputación" },
      { value: "instalaciones", label: "Instalaciones" },
      { value: "nivel_academico", label: "Nivel académico" },
      { value: "seguimiento", label: "Seguimiento comercial" },
      { value: "respuesta", label: "Respuesta tardía" },
      { value: "valor_difuso", label: "Propuesta de valor difusa" },
      { value: NO_SE, label: "No lo sé" }
    ]
  },
  {
    id: "q21",
    stage: "E",
    type: "multi",
    columns: 3,
    maxSelect: 2,
    label: "¿Cuáles son las 2 objeciones más frecuentes que reciben?",
    options: [
      { value: "precio", label: "Precio" },
      { value: "ubicacion", label: "Ubicación" },
      { value: "prestigio", label: "Prestigio/Reputación" },
      { value: "diferenciacion", label: "No perciben diferenciación" },
      { value: "tiempos", label: "Tiempos de respuesta" },
      { value: "seguimiento", label: "Seguimiento" },
      { value: "programa", label: "Programa académico" },
      { value: NO_SE, label: "No lo sé" }
    ]
  },
  {
    id: "q22",
    stage: "E",
    type: "single",
    label: "¿Sus mejores inscritos vienen más por referidos, anuncios, orgánico o base reactivada?",
    options: [
      { value: "referidos", label: "Referidos" },
      { value: "anuncios", label: "Anuncios" },
      { value: "organico", label: "Orgánico" },
      { value: "base_reactivada", label: "Base reactivada" },
      { value: NO_SE, label: "No lo sé" }
    ]
  },
  {
    id: "q23",
    stage: "E",
    type: "single",
    label: "¿Su propuesta de valor está clara y unificada en todos los canales?",
    options: [
      { value: "clara", label: "Sí, clara y unificada" },
      { value: "difusa", label: "No, es difusa" },
      { value: NO_SE, label: "No lo sé" }
    ]
  },
  {
    id: "q24",
    stage: "F",
    type: "single",
    label: "¿Tienen espacio real para crecer si mejoran admisiones?",
    options: yesNoUnknown
  },
  { id: "q25", stage: "F", type: "number", label: "¿Cuánto cuesta la colegiatura promedio?" },
  { id: "q27", stage: "F", type: "number", label: "¿Cuántos meses promedio estudia un alumno contigo?" }
];

const stepOrder = ["basic", ...questions.map((q) => q.id)];

const refs = {
  welcome: document.getElementById("welcome-screen"),
  diagnostic: document.getElementById("diagnostic-screen"),
  results: document.getElementById("results-screen"),
  startBtn: document.getElementById("start-btn"),
  prevBtn: document.getElementById("prev-btn"),
  nextBtn: document.getElementById("next-btn"),
  stepLabel: document.getElementById("step-label"),
  progressLabel: document.getElementById("progress-label"),
  progressBar: document.getElementById("progress-bar"),
  stageChip: document.getElementById("stage-chip"),
  institutionPill: document.getElementById("institution-pill"),
  questionTitle: document.getElementById("question-title"),
  questionHelp: document.getElementById("question-help"),
  validationMessage: document.getElementById("validation-message"),
  questionInput: document.getElementById("question-input"),
  findingsGrid: document.getElementById("findings-grid"),
  flowChain: document.getElementById("flow-chain"),
  funnelInsight: document.getElementById("funnel-insight"),
  funnelVisual: document.getElementById("funnel-visual"),
  diagnosticNote: document.getElementById("diagnostic-note"),
  downloadBtn: document.getElementById("download-btn"),
  resetBtn: document.getElementById("reset-btn"),
  constanzaWhatsappEmoji: document.getElementById("constanza-whatsapp-emoji"),
  resultsTitle: document.getElementById("results-title"),
  resultsClosingTitle: document.getElementById("results-closing-title")
};

let funnelAnimationToken = 0;
let activeFunnelDrag = null;

initialize();

function initialize() {
  const maxStep = stepOrder.length - 1;
  if (!Number.isInteger(state.currentStep) || state.currentStep < 0 || state.currentStep > maxStep) {
    state.currentStep = 0;
  }

  refs.startBtn.addEventListener("click", startDiagnostic);
  refs.prevBtn.addEventListener("click", onPrev);
  refs.nextBtn.addEventListener("click", onNext);
  refs.downloadBtn.addEventListener("click", () => generateAndDownloadReport(false));
  if (refs.resetBtn) {
    refs.resetBtn.addEventListener("click", resetDiagnosticSession);
  }
  startConstanzaEmojiLoop();

  if (state.currentStep > 0 || state.finishedAt) {
    refs.welcome.classList.add("hidden");
    refs.diagnostic.classList.remove("hidden");
    renderCurrentStep();
  }

  if (state.finishedAt && state.diagnosticResult) {
    showResults();
  }

  updateInstitutionPill();
  saveState();
}

function startDiagnostic() {
  if (!state.startedAt) {
    state.startedAt = new Date().toISOString();
  }
  if (!Number.isInteger(state.currentStep)) {
    state.currentStep = 0;
  }
  refs.welcome.classList.add("hidden");
  refs.results.classList.add("hidden");
  refs.diagnostic.classList.remove("hidden");
  renderCurrentStep();
  saveState();
}

function resetDiagnosticSession() {
  cleanupPremiumPrintFrame();
  localStorage.removeItem(STORAGE_KEY);
  window.location.reload();
}

function onPrev() {
  if (state.currentStep > 0) {
    state.currentStep -= 1;
    renderCurrentStep();
    saveState();
  }
}

function onNext() {
  const validation = getCurrentStepValidation();
  if (!validation.ok) {
    setValidationMessage(validation.message || "Completa este paso para avanzar.");
    return;
  }

  if (state.currentStep < stepOrder.length - 1) {
    state.currentStep += 1;
    renderCurrentStep();
    saveState();
    return;
  }

  finalizeDiagnostic();
}

function finalizeDiagnostic() {
  const metrics = computeMetrics();
  const diagnosticResult = computeDiagnostic(metrics);
  state.metrics = metrics;
  state.diagnosticResult = diagnosticResult;
  state.finishedAt = new Date().toISOString();
  saveState();
  showResults();
  generateAndDownloadReport(true);
}

function showResults() {
  refs.diagnostic.classList.add("hidden");
  refs.results.classList.remove("hidden");
  renderResults();
}

function renderCurrentStep() {
  const totalSteps = stepOrder.length;
  const current = state.currentStep + 1;
  const progress = Math.round((current / totalSteps) * 100);
  refs.progressLabel.textContent = `${progress}%`;
  refs.progressBar.style.width = `${progress}%`;
  pulseProgress();
  refs.prevBtn.disabled = state.currentStep === 0;
  setValidationMessage("");
  updateInstitutionPill();

  const stepKey = stepOrder[state.currentStep];
  refs.stepLabel.textContent = `Paso ${current} de ${totalSteps}`;

  if (stepKey === "basic") {
    refs.stageChip.textContent = stages.basic;
    refs.questionTitle.textContent = "Pregunta 0 — URL y datos básicos";
    refs.questionHelp.textContent = "Se guarda automáticamente desde este punto.";
    refs.nextBtn.textContent = "Continuar →";
    refs.questionInput.innerHTML = "";
    renderBasicFields();
    animateQuestionCard();
    return;
  }

  const q = getQuestion(stepKey);
  refs.stageChip.textContent = stages[q.stage];
  refs.questionTitle.textContent = q.label;
  refs.questionHelp.textContent = "Tus respuestas nos permiten encontrar el cuello más probable del sistema.";
  refs.nextBtn.textContent = state.currentStep === totalSteps - 1 ? "Ver resultados →" : "Continuar →";
  refs.questionInput.innerHTML = "";
  renderQuestion(q);
  animateQuestionCard();
}

function renderBasicFields() {
  const fields = [
    { id: "institutionUrl", label: "URL institucional", type: "url", placeholder: "https://www.tuinstitucion.edu.mx" },
    { id: "institutionName", label: "Nombre de la institución", type: "text", placeholder: "Ej. Colegio La Paz" },
    { id: "yearsOperating", label: "Años de existencia", type: "number", placeholder: "Ej. 12" },
    { id: "fullName", label: "Nombre completo", type: "text", placeholder: "Ej. Ana Martínez" },
    { id: "phone", label: "Celular", type: "text", placeholder: "Ej. 8112345678" },
    { id: "email", label: "Correo", type: "email", placeholder: "ejemplo@institucion.edu.mx" }
  ];

  const wrapper = document.createElement("div");
  wrapper.className = "input-group";

  fields.forEach((field) => {
    const group = document.createElement("div");
    group.className = "input-group";

    const label = document.createElement("label");
    label.textContent = field.label;

    const input = document.createElement("input");
    input.type = field.type;
    input.placeholder = field.placeholder;
    input.value = state.basicData[field.id] || "";
    input.addEventListener("input", () => {
      state.basicData[field.id] = input.value.trim();
      if (field.id === "institutionName") {
        updateInstitutionPill();
      }
      saveState();
    });

    group.appendChild(label);
    group.appendChild(input);
    wrapper.appendChild(group);
  });

  refs.questionInput.appendChild(wrapper);
}

function renderQuestion(question) {
  if (question.type === "text" || question.type === "textarea") {
    renderFreeText(question);
    return;
  }

  if (question.type === "number") {
    if (question.id === "q6") {
      renderLeadCadence(question);
      return;
    }
    if (question.id === "q25") {
      renderTuitionQuestion(question);
      return;
    }
    renderNumber(question);
    return;
  }

  if (question.type === "single") {
    renderSingleChoice(question);
    return;
  }

  if (question.type === "multi") {
    renderMultiChoice(question);
  }
}

function renderFreeText(question) {
  const field = document.createElement(question.type === "textarea" ? "textarea" : "input");
  if (question.type === "text") field.type = "text";
  field.placeholder = "Escribe aquí";
  const value = state.responses[question.id];
  field.value = value && value !== NO_SE ? value : "";

  field.addEventListener("input", () => {
    state.responses[question.id] = field.value.trim();
    saveState();
  });

  const helperRow = document.createElement("div");
  helperRow.className = "helper-row";

  const btn = createOptionButton("No lo sé", value === NO_SE, () => {
    state.responses[question.id] = NO_SE;
    field.value = "";
    saveState();
    renderCurrentStep();
  });

  helperRow.appendChild(btn);
  refs.questionInput.appendChild(field);
  refs.questionInput.appendChild(helperRow);
}

function renderNumber(question) {
  const field = document.createElement("input");
  field.type = "number";
  field.placeholder = "Ingresa un número";

  const value = state.responses[question.id];
  field.value = typeof value === "number" ? value : "";

  field.addEventListener("input", () => {
    const v = Number(field.value);
    if (!Number.isNaN(v) && field.value !== "") {
      state.responses[question.id] = v;
    } else {
      state.responses[question.id] = "";
    }
    saveState();
  });

  const helperRow = document.createElement("div");
  helperRow.className = "helper-row";

  const helper = document.createElement("p");
  helper.className = "helper-text";
  helper.textContent = "No necesitas tener todos los números para avanzar.";

  const btn = createOptionButton("No lo sé", value === NO_SE, () => {
    state.responses[question.id] = NO_SE;
    field.value = "";
    saveState();
    renderCurrentStep();
  });

  helperRow.appendChild(btn);
  helperRow.appendChild(helper);
  refs.questionInput.appendChild(field);
  refs.questionInput.appendChild(helperRow);
}

function renderLeadCadence(question) {
  const normalized = getNormalizedLeadCadence();
  const grid = document.createElement("div");
  grid.className = "lead-cadence-grid";

  const fields = [
    { key: "daily", label: "Leads por día" },
    { key: "monthly", label: "Leads por mes" },
    { key: "yearly", label: "Leads por año" }
  ];

  fields.forEach((item) => {
    const group = document.createElement("div");
    group.className = "input-group";
    const label = document.createElement("label");
    label.textContent = item.label;
    const input = document.createElement("input");
    input.type = "number";
    input.step = "0.01";
    input.min = "0";
    input.placeholder = "0";
    input.value = normalized[item.key] === "" ? "" : String(normalized[item.key]);
    input.addEventListener("input", () => {
      applyLeadCadenceInput(item.key, input.value);
    });
    group.appendChild(label);
    group.appendChild(input);
    grid.appendChild(group);
  });

  const helper = document.createElement("p");
  helper.className = "helper-text";
  helper.textContent = "Se calculan automáticamente con 1 mes = 30.4 días y 1 año = 365 días. Para el diagnóstico usamos leads por mes como base.";

  const helperRow = document.createElement("div");
  helperRow.className = "helper-row";
  const btn = createOptionButton("No lo sé", state.responses[question.id] === NO_SE, () => {
    state.responses[question.id] = NO_SE;
    state.leadCadence = { daily: "", monthly: "", yearly: "" };
    saveState();
    renderCurrentStep();
  });
  helperRow.appendChild(btn);

  refs.questionInput.appendChild(grid);
  refs.questionInput.appendChild(helper);
  refs.questionInput.appendChild(helperRow);
}

function renderTuitionQuestion(question) {
  const wrapper = document.createElement("div");
  wrapper.className = "input-group";

  const label = document.createElement("label");
  label.textContent = "Colegiatura promedio";

  const row = document.createElement("div");
  row.className = "currency-row";

  const amountInput = document.createElement("input");
  amountInput.type = "number";
  amountInput.step = "0.01";
  amountInput.min = "0";
  amountInput.placeholder = "Ingresa un monto";
  amountInput.value = state.tuitionInput.amount === "" ? "" : String(state.tuitionInput.amount);

  const currencySelect = document.createElement("select");
  currencySelect.innerHTML = `
    <option value="MXN">MXN</option>
    <option value="USD">USD</option>
    <option value="COL">COL</option>
  `;
  currencySelect.value = state.tuitionInput.currency || "MXN";

  amountInput.addEventListener("input", () => {
    applyTuitionInput(amountInput.value, currencySelect.value);
  });

  currencySelect.addEventListener("change", () => {
    const prevCurrency = state.tuitionInput.currency || "MXN";
    const nextCurrency = currencySelect.value;
    const currentAmount = Number(state.tuitionInput.amount);

    if (state.tuitionInput.amount !== "" && Number.isFinite(currentAmount)) {
      const converted = convertCurrency(currentAmount, prevCurrency, nextCurrency);
      amountInput.value = String(roundCadence(converted));
      applyTuitionInput(amountInput.value, nextCurrency);
    } else {
      state.tuitionInput.currency = nextCurrency;
      saveState();
    }
  });

  row.appendChild(amountInput);
  row.appendChild(currencySelect);

  const helper = document.createElement("p");
  helper.className = "helper-text";
  helper.textContent = "Moneda base: MXN. Puedes capturar en USD o COL y convertimos automáticamente con tipo de cambio referencial.";

  const helperRow = document.createElement("div");
  helperRow.className = "helper-row";
  const btn = createOptionButton("No lo sé", state.responses[question.id] === NO_SE, () => {
    state.responses[question.id] = NO_SE;
    state.tuitionInput = { amount: "", currency: "MXN" };
    saveState();
    renderCurrentStep();
  });
  helperRow.appendChild(btn);

  wrapper.appendChild(label);
  wrapper.appendChild(row);
  wrapper.appendChild(helper);
  refs.questionInput.appendChild(wrapper);
  refs.questionInput.appendChild(helperRow);
}

function applyTuitionInput(rawAmount, currency) {
  const amount = Number(rawAmount);
  if (rawAmount === "" || Number.isNaN(amount) || amount < 0) {
    state.tuitionInput.amount = "";
    state.tuitionInput.currency = currency || "MXN";
    state.responses.q25 = "";
    saveState();
    return;
  }

  const safeCurrency = currency || "MXN";
  const mxnAmount = convertCurrency(amount, safeCurrency, "MXN");

  state.tuitionInput.amount = roundCadence(amount);
  state.tuitionInput.currency = safeCurrency;
  state.responses.q25 = roundCadence(mxnAmount);
  saveState();
}

function applyLeadCadenceInput(unit, rawValue) {
  const value = Number(rawValue);
  if (rawValue === "" || Number.isNaN(value) || value < 0) {
    state.leadCadence = { daily: "", monthly: "", yearly: "" };
    state.responses.q6 = "";
    saveState();
    renderCurrentStep();
    return;
  }

  let daily = null;
  if (unit === "daily") daily = value;
  if (unit === "monthly") daily = value / DAYS_PER_MONTH;
  if (unit === "yearly") daily = value / DAYS_PER_YEAR;

  const monthly = daily * DAYS_PER_MONTH;
  const yearly = daily * DAYS_PER_YEAR;

  state.leadCadence = {
    daily: roundCadence(daily),
    monthly: roundCadence(monthly),
    yearly: roundCadence(yearly)
  };

  state.responses.q6 = roundCadence(monthly);
  saveState();
  renderCurrentStep();
}

function getNormalizedLeadCadence() {
  const cadence = state.leadCadence || {};
  const hasCadence = ["daily", "monthly", "yearly"].some((k) => cadence[k] !== "" && Number.isFinite(Number(cadence[k])));
  if (hasCadence) {
    return {
      daily: cadence.daily === "" ? "" : roundCadence(Number(cadence.daily)),
      monthly: cadence.monthly === "" ? "" : roundCadence(Number(cadence.monthly)),
      yearly: cadence.yearly === "" ? "" : roundCadence(Number(cadence.yearly))
    };
  }

  if (typeof state.responses.q6 === "number" && Number.isFinite(state.responses.q6)) {
    const monthly = state.responses.q6;
    const daily = monthly / DAYS_PER_MONTH;
    const yearly = daily * DAYS_PER_YEAR;
    return {
      daily: roundCadence(daily),
      monthly: roundCadence(monthly),
      yearly: roundCadence(yearly)
    };
  }

  return { daily: "", monthly: "", yearly: "" };
}

function roundCadence(value) {
  if (!Number.isFinite(value)) return "";
  return Math.round(value * 100) / 100;
}

function renderSingleChoice(question) {
  const value = state.responses[question.id];
  const grid = document.createElement("div");
  grid.className = "option-grid";
  if (question.columns === 3) {
    grid.classList.add("option-grid-3");
  }

  question.options.forEach((opt) => {
    const button = createOptionButton(opt.label, value === opt.value, () => {
      state.responses[question.id] = opt.value;
      saveState();
      renderCurrentStep();
      const shouldAutoAdvance = question.autoAdvance !== false;
      if (shouldAutoAdvance) {
        setTimeout(() => onNext(), 120);
      }
    });
    grid.appendChild(button);
  });

  refs.questionInput.appendChild(grid);
}

function renderMultiChoice(question) {
  const selected = Array.isArray(state.responses[question.id]) ? [...state.responses[question.id]] : [];
  const grid = document.createElement("div");
  grid.className = "option-grid";
  if (question.columns === 3) {
    grid.classList.add("option-grid-3");
  }

  question.options.forEach((opt) => {
    const button = createOptionButton(opt.label, selected.includes(opt.value), () => {
      let next = Array.isArray(state.responses[question.id]) ? [...state.responses[question.id]] : [];

      if (opt.value === NO_SE) {
        next = [NO_SE];
      } else {
        next = next.filter((v) => v !== NO_SE);
        if (next.includes(opt.value)) {
          next = next.filter((v) => v !== opt.value);
        } else if (!question.maxSelect || next.length < question.maxSelect) {
          next.push(opt.value);
        }
      }

      state.responses[question.id] = next;
      saveState();
      renderCurrentStep();
    });
    grid.appendChild(button);
  });

  const helper = document.createElement("p");
  helper.className = "helper-text";
  helper.textContent = question.maxSelect
    ? `Selecciona hasta ${question.maxSelect} opciones.`
    : "Puedes seleccionar varias opciones.";

  refs.questionInput.appendChild(grid);
  refs.questionInput.appendChild(helper);
}

function createOptionButton(text, selected, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `option-btn${selected ? " selected" : ""}`;
  button.textContent = text;
  button.addEventListener("click", onClick);
  return button;
}

function isCurrentStepValid() {
  return getCurrentStepValidation().ok;
}

function getCurrentStepValidation() {
  const stepKey = stepOrder[state.currentStep];
  if (stepKey === "basic") {
    const institutionUrl = (state.basicData.institutionUrl || "").trim();
    const institution = (state.basicData.institutionName || "").trim();
    const fullName = (state.basicData.fullName || "").trim();
    const phone = (state.basicData.phone || "").trim();
    const email = (state.basicData.email || "").trim();

    if (!institutionUrl || !institution || !fullName || !phone || !email) {
      return { ok: false, message: "Completa primero la URL institucional y después nombre, celular y correo." };
    }
    if (!looksLikeUrl(institutionUrl)) {
      return { ok: false, message: "La URL parece inválida. Usa un formato como https://www.tuinstitucion.edu.mx" };
    }
    if (!looksLikeEmail(email)) {
      return { ok: false, message: "El correo parece inválido. Revísalo para evitar un reporte incompleto." };
    }
    if (!looksLikePhone(phone)) {
      return { ok: false, message: "El celular parece inválido. Ingresa al menos 8 dígitos." };
    }
    return { ok: true, message: "" };
  }

  const q = getQuestion(stepKey);
  const value = state.responses[q.id];

  if (q.type === "multi") {
    return {
      ok: Array.isArray(value) && value.length > 0,
      message: "Selecciona al menos una opción o marca 'No lo sé'."
    };
  }

  if (q.type === "number") {
    return {
      ok: value === NO_SE || typeof value === "number",
      message: "Ingresa un número o marca 'No lo sé'."
    };
  }

  if (q.type === "text" || q.type === "textarea") {
    return {
      ok: value === NO_SE || (typeof value === "string" && value.trim().length > 0),
      message: "Escribe una respuesta breve o marca 'No lo sé'."
    };
  }

  return {
    ok: (typeof value === "string" && value.length > 0) || typeof value === "number",
    message: "Selecciona una opción para continuar."
  };
}

function setValidationMessage(message) {
  if (!refs.validationMessage) return;
  if (!message) {
    refs.validationMessage.textContent = "";
    refs.validationMessage.classList.add("hidden");
    return;
  }
  refs.validationMessage.textContent = message;
  refs.validationMessage.classList.remove("hidden");
}

function updateInstitutionPill() {
  if (!refs.institutionPill) return;
  const name = (state.basicData.institutionName || "").trim();
  if (!name) {
    refs.institutionPill.classList.add("hidden");
    refs.institutionPill.textContent = "";
    return;
  }
  refs.institutionPill.textContent = `Institución: ${name}`;
  refs.institutionPill.classList.remove("hidden");
}

function looksLikeEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || "").trim());
}

function looksLikePhone(value) {
  const digits = String(value || "").replace(/\D/g, "");
  return digits.length >= 8;
}

function looksLikeUrl(value) {
  const raw = String(value || "").trim();
  if (!raw) return false;
  const normalized = /^https?:\/\//i.test(raw) ? raw : `https://${raw}`;
  try {
    const u = new URL(normalized);
    return Boolean(u.hostname && u.hostname.includes("."));
  } catch (_error) {
    return false;
  }
}

function getQuestion(id) {
  return questions.find((q) => q.id === id);
}

function toNumber(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function percent(numerator, denominator) {
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator) || denominator <= 0) {
    return null;
  }
  return numerator / denominator;
}

function pct(value) {
  if (!Number.isFinite(value)) return "N/D";
  return `${Math.round(value * 100)}%`;
}

function getAnswerLabel(question, value) {
  if (question && question.id === "q25") {
    return getTuitionDisplayValue(value);
  }
  if (Array.isArray(value)) {
    return value.map((v) => getSingleLabel(question, v)).join(", ");
  }
  return getSingleLabel(question, value);
}

function getTuitionDisplayValue(mxnValue) {
  if (mxnValue === NO_SE) return "No lo sé";
  if (!Number.isFinite(Number(mxnValue))) return "Sin respuesta";
  const inputAmount = Number(state.tuitionInput.amount);
  const inputCurrency = state.tuitionInput.currency || "MXN";
  if (Number.isFinite(inputAmount)) {
    return `${formatMoneyByCurrency(inputAmount, inputCurrency)} (equiv. ${formatMoneyByCurrency(Number(mxnValue), "MXN")})`;
  }
  return formatMoneyByCurrency(Number(mxnValue), "MXN");
}

function getSingleLabel(question, value) {
  if (value === NO_SE) return "No lo sé";
  if (value === null || value === undefined || value === "") return "Sin respuesta";
  if (question.type === "single" || question.type === "multi") {
    const found = question.options.find((opt) => opt.value === value);
    return found ? found.label : String(value);
  }
  return String(value);
}

function computeMetrics() {
  const r = state.responses;
  const leads = toNumber(r.q6);
  const contactRateInput = toNumber(r.q7);
  const appointmentRateInput = toNumber(r.q8);
  const attendedRateInput = toNumber(r.q9);
  let contacted = null;
  if (Number.isFinite(leads) && Number.isFinite(contactRateInput)) {
    contacted = contactRateInput <= 100
      ? roundCadence(leads * (contactRateInput / 100))
      : contactRateInput;
  }
  let appointments = null;
  if (Number.isFinite(contacted) && Number.isFinite(appointmentRateInput)) {
    appointments = appointmentRateInput <= 100
      ? roundCadence(contacted * (appointmentRateInput / 100))
      : appointmentRateInput;
  }
  let attended = null;
  if (Number.isFinite(appointments) && Number.isFinite(attendedRateInput)) {
    attended = attendedRateInput <= 100
      ? roundCadence(appointments * (attendedRateInput / 100))
      : attendedRateInput;
  }
  const enrolled = toNumber(r.q10);
  const currentStudents = toNumber(r.q3);
  const targetNew = toNumber(r.q4);
  const capacity = toNumber(r.q5);
  const averageTuition = toNumber(r.q25);
  const averageMonths = toNumber(r.q27);
  const valuePerSeat = Number.isFinite(averageTuition) && Number.isFinite(averageMonths) && averageMonths > 0
    ? roundCadence(averageTuition * averageMonths)
    : averageTuition;

  const metrics = {
    leads,
    contacted,
    appointments,
    attended,
    enrolled,
    targetNew,
    currentStudents,
    capacity,
    averageTuition,
    averageMonths,
    valuePerSeat,
    lead_to_contact_rate: percent(contacted, leads),
    lead_to_appointment_rate: percent(appointments, leads),
    contacted_to_appointment_rate: percent(appointments, contacted),
    appointment_to_attended_rate: percent(attended, appointments),
    attended_to_enrolled_rate: percent(enrolled, attended),
    lead_to_enrolled_rate: percent(enrolled, leads)
  };

  applyFunnelSanity(metrics);

  metrics.capacity_available = Number.isFinite(capacity) && Number.isFinite(currentStudents)
    ? Math.max(capacity - currentStudents, 0)
    : null;

  metrics.lead_sufficiency = Number.isFinite(leads) && Number.isFinite(targetNew) && Number.isFinite(metrics.lead_to_enrolled_rate)
    ? leads * metrics.lead_to_enrolled_rate >= targetNew
    : null;

  metrics.projected_new_enrolled = Number.isFinite(leads) && Number.isFinite(metrics.lead_to_enrolled_rate)
    ? leads * metrics.lead_to_enrolled_rate
    : null;

  const structuralSignals = [];
  if (r.q17 === "no") structuralSignals.push("No usan CRM");
  if (r.q18 === "si") structuralSignals.push("Operación separada en Excel/WhatsApp/correo/llamadas");
  if (r.q19 === "no") structuralSignals.push("No tienen tablero por etapa");
  if (r.q16 === "no") structuralSignals.push("No hay automatización de seguimiento");
  if (r.q14 === "fragmentado") structuralSignals.push("Canales fragmentados");
  if (r.q15 === "dificil") structuralSignals.push("Agenda con fricción");

  metrics.structural_disorder_score = structuralSignals.length;
  metrics.structural_disorder_signals = structuralSignals;

  const qualityNumeric = ["q3", "q4", "q5", "q6", "q7", "q8", "q9", "q10", "q25", "q27"];
  const answeredNumeric = qualityNumeric.filter((key) => typeof r[key] === "number").length;
  const completenessScore = answeredNumeric / qualityNumeric.length;
  const consistencyScore = Math.max(0, 1 - (metrics.funnel_inconsistency_count / 5));
  metrics.data_quality_score = (completenessScore * 0.8) + (consistencyScore * 0.2);

  const availableRates = [
    metrics.lead_to_contact_rate,
    metrics.contacted_to_appointment_rate,
    metrics.appointment_to_attended_rate,
    metrics.attended_to_enrolled_rate
  ].filter((x) => Number.isFinite(x)).length;
  const rateCoverage = availableRates / 4;
  const evidenceScore = (metrics.data_quality_score * 0.6) + (rateCoverage * 0.25) + ((Math.min(metrics.structural_disorder_score, 6) / 6) * 0.15);
  metrics.confidence_score = Math.max(0.2, Math.min(0.95, evidenceScore));
  metrics.break_stage = detectBreakStage(metrics);

  return metrics;
}

function applyFunnelSanity(metrics) {
  const stagesOrder = [
    { key: "leads", label: "Leads" },
    { key: "contacted", label: "Contactados" },
    { key: "appointments", label: "Citas" },
    { key: "attended", label: "Asistieron" },
    { key: "enrolled", label: "Inscritos" }
  ];
  const notes = [];

  for (let i = 1; i < stagesOrder.length; i += 1) {
    const prev = stagesOrder[i - 1];
    const cur = stagesOrder[i];
    const prevValue = metrics[prev.key];
    const curValue = metrics[cur.key];

    if (!Number.isFinite(prevValue) || !Number.isFinite(curValue)) continue;
    if (curValue > prevValue) {
      notes.push(`${cur.label} era mayor que ${prev.label}; se ajustó para mantener coherencia del embudo.`);
      metrics[cur.key] = prevValue;
    }
  }

  metrics.lead_to_contact_rate = percent(metrics.contacted, metrics.leads);
  metrics.lead_to_appointment_rate = percent(metrics.appointments, metrics.leads);
  metrics.contacted_to_appointment_rate = percent(metrics.appointments, metrics.contacted);
  metrics.appointment_to_attended_rate = percent(metrics.attended, metrics.appointments);
  metrics.attended_to_enrolled_rate = percent(metrics.enrolled, metrics.attended);
  metrics.lead_to_enrolled_rate = percent(metrics.enrolled, metrics.leads);
  metrics.funnel_notes = notes;
  metrics.funnel_inconsistency_count = notes.length;
}

function detectBreakStage(metrics) {
  const transitions = [
    { key: "lead_to_contact_rate", label: "Contactados", rate: metrics.lead_to_contact_rate },
    { key: "contacted_to_appointment_rate", label: "Citas", rate: metrics.contacted_to_appointment_rate },
    { key: "appointment_to_attended_rate", label: "Asistieron", rate: metrics.appointment_to_attended_rate },
    { key: "attended_to_enrolled_rate", label: "Inscritos", rate: metrics.attended_to_enrolled_rate }
  ].filter((t) => Number.isFinite(t.rate));

  if (!transitions.length) {
    return null;
  }
  return transitions.reduce((acc, cur) => (cur.rate < acc.rate ? cur : acc), transitions[0]);
}

function computeDiagnostic(metrics) {
  const r = state.responses;
  const candidates = [];
  const structuralTerms = ["precio", "ubicacion", "reputacion", "instalaciones", "nivel_academico", "prestigio", "programa"];

  const q20Values = Array.isArray(r.q20)
    ? r.q20.filter((v) => v !== NO_SE)
    : (typeof r.q20 === "string" && r.q20 !== NO_SE ? [r.q20] : []);
  const q21 = Array.isArray(r.q21) ? r.q21 : [];
  const structuralFromQ20 = q20Values.filter((v) => structuralTerms.includes(v)).length;
  const structuralFromQ21 = q21.filter((v) => structuralTerms.includes(v)).length;
  const structuralScore = (structuralFromQ20 * 1.5) + structuralFromQ21;
  const hasStructuralDominance = structuralScore >= 3 || (structuralScore >= 2 && structuralFromQ20 > 0);
  const structureAsBase = metrics.structural_disorder_score >= 3;

  if (hasStructuralDominance) {
    candidates.push(buildCandidate({
      bottleneck: "Hallazgo estructural",
      visibleIssue: "Factores estructurales del mercado están dominando la pérdida de prospectos",
      causeRoot: "Predominan variables institucionales (precio, ubicación, reputación, instalaciones o nivel académico) que impactan la conversión.",
      evidence: [
        `Razones dominantes de pérdida: ${getAnswerLabel(getQuestion("q20"), q20Values)}`,
        `Objeciones frecuentes: ${getAnswerLabel(getQuestion("q21"), q21)}`
      ],
      impact: "La conversión se frena por factores que no siempre se corrigen solo con software.",
      solution: "Requiere conversación estratégica integral antes de empujar herramientas.",
      products: ["Conversación estratégica con SuperLeads (sin forzar producto estándar)"],
      tags: ["Hallazgo estructural"],
      severity: 88,
      moneyCloseness: 85,
      evidenceQuality: 80,
      actionability: 35
    }));
  }

  if (structureAsBase) {
    candidates.push(buildCandidate({
      bottleneck: "Falta de estructura digital de admisiones",
      visibleIssue: "El proceso de admisiones está fragmentado y sin trazabilidad central",
      causeRoot: metrics.structural_disorder_signals.join(" + "),
      evidence: metrics.structural_disorder_signals,
      impact: "Se pierde velocidad, seguimiento y control del embudo completo.",
      solution: "Instalar base operativa y ordenar puntos de entrada.",
      products: ["CRM SuperLeads", "Optimización de Puntos de Contacto"],
      tags: ["Base obligatoria", "Causa raíz"],
      severity: Math.min(92, 55 + metrics.structural_disorder_score * 8),
      moneyCloseness: 78,
      evidenceQuality: 82,
      actionability: 93
    }));
  }

  const hasCapacity = metrics.capacity_available !== null && metrics.capacity_available > 0;
  const needMore = Number.isFinite(metrics.targetNew) && Number.isFinite(metrics.enrolled) && metrics.targetNew > metrics.enrolled;
  const projectedBelowGoal = Number.isFinite(metrics.projected_new_enrolled) && Number.isFinite(metrics.targetNew) && metrics.projected_new_enrolled < metrics.targetNew;

  if (hasCapacity && needMore && projectedBelowGoal) {
    const deficit = metrics.targetNew - metrics.projected_new_enrolled;
    const severity = Math.min(95, 50 + (deficit / Math.max(metrics.targetNew, 1)) * 45);
    const products = ["Campañas Integrales de Generación de Demanda"];
    if (metrics.structural_disorder_score >= 3 || r.q17 === "no") {
      products.push("CRM SuperLeads (base operativa)");
    }

    candidates.push(buildCandidate({
      bottleneck: "Falta de prospectos",
      visibleIssue: "El volumen de leads no alcanza para llegar a la meta con la conversión actual",
      causeRoot: "Demanda insuficiente para el objetivo comercial del periodo.",
      evidence: [
        `Meta de nuevos inscritos: ${safeNum(metrics.targetNew)}`,
        `Inscritos proyectados con conversión actual: ${safeNum(metrics.projected_new_enrolled)}`,
        `Capacidad disponible: ${safeNum(metrics.capacity_available)}`
      ],
      impact: "Aun optimizando cierre, el flujo de entrada no alcanza para crecer al ritmo esperado.",
      solution: "Generar demanda estructurada con base medible.",
      products,
      tags: ["Principal potencial"],
      severity,
      moneyCloseness: 76,
      evidenceQuality: 75,
      actionability: 86
    }));
  }

  const lowCitas = (isLow(metrics.lead_to_contact_rate, 0.55) || isLow(metrics.lead_to_appointment_rate, 0.35) || isLow(metrics.contacted_to_appointment_rate, 0.55));
  if (Number.isFinite(metrics.leads) && metrics.leads > 0 && lowCitas) {
    const rootCauses = [];
    if (r.q11 === "mas_2_horas" || r.q11 === "mismo_dia") rootCauses.push("respuesta lenta");
    if (r.q12 === "solo_horario") rootCauses.push("solo atienden en horario fijo");
    if (r.q13 === "no") rootCauses.push("no usan IA conversacional");
    if (r.q15 === "dificil") rootCauses.push("agenda difícil");
    if (r.q14 === "fragmentado") rootCauses.push("canales fragmentados");
    if (r.q16 === "no") rootCauses.push("seguimiento débil");
    if (r.q23 === "difusa") rootCauses.push("propuesta de valor difusa");
    if (rootCauses.length === 0) rootCauses.push("fricción de activación comercial");
    if (structureAsBase && !rootCauses.includes("falta de estructura digital")) {
      rootCauses.push("falta de estructura digital");
    }

    const products = [];
    const rootText = rootCauses.join(" + ");

    if (rootText.includes("respuesta lenta") || rootText.includes("horario fijo") || rootText.includes("IA conversacional")) {
      products.push("CRM SuperLeads", "IA Conversacional de SuperLeads");
    }
    if (rootText.includes("seguimiento débil")) products.push("Seguimiento Comercial");
    if (rootText.includes("propuesta de valor difusa")) products.push("Documento Central de Estrategia");
    if (rootText.includes("agenda difícil")) products.push("Optimización de Puntos de Contacto");
    if (rootText.includes("canales fragmentados")) products.push("Optimización de Puntos de Contacto");
    if (products.length === 0) products.push("Dirección Estratégica del Sistema de Inscripciones");

    candidates.push(buildCandidate({
      bottleneck: "Baja cantidad de citas",
      visibleIssue: "Entran leads, pero pocos avanzan a cita/visita/entrevista",
      causeRoot: rootText,
      evidence: [
        `Lead → Contactado: ${pct(metrics.lead_to_contact_rate)}`,
        `Lead → Cita: ${pct(metrics.lead_to_appointment_rate)}`,
        `Contactado → Cita: ${pct(metrics.contacted_to_appointment_rate)}`,
        structureAsBase ? "La caída visible de citas se explica por una base digital fragmentada." : "La caída principal ocurre antes de la cita."
      ],
      impact: "Sin citas suficientes, el pipeline se queda sin oportunidades de cierre.",
      solution: "Recuperar velocidad de respuesta y fricción de avance a cita.",
      products: dedupe(products),
      tags: ["Cuello visible", "Causa raíz", structureAsBase ? "Base obligatoria" : "Accionable"],
      severity: 84,
      moneyCloseness: 86,
      evidenceQuality: 88,
      actionability: 90
    }));
  }

  if (Number.isFinite(metrics.appointments) && metrics.appointments > 0 && isLow(metrics.attended_to_enrolled_rate, 0.35)) {
    const rootCauses = [];
    if (q20Values.some((v) => ["precio", "ubicacion", "reputacion", "instalaciones", "nivel_academico"].includes(v))) {
      rootCauses.push("precio o condiciones de mercado dominan");
    }
    if ((Array.isArray(r.q21) ? r.q21 : []).includes("precio")) rootCauses.push("objeciones de precio mal manejadas");
    if ((Array.isArray(r.q21) ? r.q21 : []).includes("seguimiento") || r.q16 === "no") rootCauses.push("seguimiento post-cita flojo");
    if ((Array.isArray(r.q21) ? r.q21 : []).includes("diferenciacion") || r.q23 === "difusa") rootCauses.push("discurso comercial débil");
    if (rootCauses.length === 0) rootCauses.push("cierre comercial inconsistente");

    const products = ["Taller \"Inscripción es Cuestión de Ventas\""];
    if (rootCauses.join(" ").includes("post-cita")) products.push("Seguimiento Comercial");

    candidates.push(buildCandidate({
      bottleneck: "Baja tasa de cierre en la cita",
      visibleIssue: "Sí llegan a cita y asisten, pero pocas citas se convierten en inscripción",
      causeRoot: rootCauses.join(" + "),
      evidence: [
        `Cita → Asistencia: ${pct(metrics.appointment_to_attended_rate)}`,
        `Asistencia → Inscripción: ${pct(metrics.attended_to_enrolled_rate)}`
      ],
      impact: "El esfuerzo comercial no se traduce en ingreso final.",
      solution: "Mejorar cierre y manejo comercial de objeciones.",
      products,
      tags: ["Cierre"],
      severity: 86,
      moneyCloseness: 95,
      evidenceQuality: 84,
      actionability: 89
    }));
  }

  const rates = [
    metrics.lead_to_contact_rate,
    metrics.contacted_to_appointment_rate,
    metrics.appointment_to_attended_rate,
    metrics.attended_to_enrolled_rate
  ];
  const dominantBreak = metrics.break_stage;
  const severeStage = rates.some((v, i) => {
    const thresholds = [0.4, 0.3, 0.55, 0.25];
    return isLow(v, thresholds[i]);
  });

  if (Number.isFinite(metrics.leads) && metrics.leads > 0 && isLow(metrics.lead_to_enrolled_rate, 0.08) && !severeStage) {
    const distributed = rates.filter((v) => isLow(v, 0.62)).length >= 2;
    const noSingleCulprit = !dominantBreak || dominantBreak.rate > 0.45;
    if (distributed && noSingleCulprit) {
      const products = ["Dirección Estratégica del Sistema de Inscripciones"];
      if (metrics.structural_disorder_score >= 3 || r.q17 === "no") {
        products.push("CRM SuperLeads");
      }

      candidates.push(buildCandidate({
        bottleneck: "Baja conversión de lead a inscrito",
        visibleIssue: "Entra interés, pero el sistema completo no está convirtiendo bien",
        causeRoot: "sistema incompleto + fuga distribuida + falta de dirección",
        evidence: [
          `Lead → Inscrito: ${pct(metrics.lead_to_enrolled_rate)}`,
          `Fugas en varias etapas sin un único quiebre dominante`,
          dominantBreak ? `Ruptura más fuerte detectada: ${dominantBreak.label} (${pct(dominantBreak.rate)})` : "No hay ruptura dominante por etapa"
        ],
        impact: "La pérdida está repartida y erosiona todo el embudo.",
        solution: "Dar dirección al sistema completo de inscripciones.",
        products,
        tags: ["Sistema completo"],
        severity: 82,
        moneyCloseness: 91,
        evidenceQuality: 80,
        actionability: 83
      }));
    }
  }

  if (candidates.length === 0) {
    candidates.push(buildCandidate({
      bottleneck: "Hallazgo estructural",
      visibleIssue: "Información insuficiente para afirmar un cuello único",
      causeRoot: "calidad de dato limitada en esta primera radiografía",
      evidence: ["No hay evidencia suficiente para priorizar un único cuello con alta confianza."],
      impact: "Se requiere completar datos para prescribir con precisión.",
      solution: "Diagnóstico preliminar y conversación estratégica guiada.",
      products: ["Sesión de Dirección Estratégica del Sistema de Inscripciones"],
      tags: ["Diagnóstico preliminar"],
      severity: 50,
      moneyCloseness: 50,
      evidenceQuality: 35,
      actionability: 60
    }));
  }

  const ranked = rankCandidates(candidates);

  const principal = ranked[0];
  const secondary = ranked.slice(1, 3);
  const status = metrics.data_quality_score < 0.45 ? "Diagnóstico preliminar" : "Diagnóstico con evidencia suficiente";

  return {
    status,
    principal,
    secondary,
    all: ranked.slice(0, 3)
  };
}

function buildCandidate(payload) {
  return {
    ...payload,
    products: normalizeRecommendedProducts(payload.products || [], payload),
    score: 0
  };
}

function normalizeRecommendedProducts(products, context = {}) {
  const input = Array.isArray(products) ? products : [];
  const normalized = [];

  input.forEach((product) => {
    const raw = String(product || "").trim();
    if (!raw) return;
    if (PRODUCT_NAME_SET.has(raw)) {
      normalized.push(raw);
      return;
    }
    const mapped = PRODUCT_ALIAS_MAP[raw];
    if (Array.isArray(mapped)) {
      mapped.forEach((name) => {
        if (PRODUCT_NAME_SET.has(name)) normalized.push(name);
      });
    }
  });

  const defaults = getDefaultProductsForBottleneck(context.bottleneck);
  if (!normalized.length) {
    defaults.forEach((name) => normalized.push(name));
  }

  const wantThree = shouldUseThreeProducts(context, normalized);
  const targetCount = wantThree ? MAX_RECOMMENDED_PRODUCTS : DEFAULT_RECOMMENDED_PRODUCTS;

  defaults.forEach((name) => {
    if (normalized.length < targetCount && !normalized.includes(name)) {
      normalized.push(name);
    }
  });

  for (const catalogItem of PRODUCT_CATALOG) {
    if (normalized.length >= targetCount) break;
    if (!normalized.includes(catalogItem.name)) {
      normalized.push(catalogItem.name);
    }
  }

  return dedupe(normalized).slice(0, Math.min(targetCount, MAX_RECOMMENDED_PRODUCTS));
}

function getProductMeta(productName) {
  return PRODUCT_BY_NAME[productName] || {
    name: productName,
    emoji: "🧩",
    description: "Producto SuperLeads recomendado para fortalecer esta parte del sistema."
  };
}

function renderProductsContainersHtml(products) {
  const list = Array.isArray(products) && products.length
    ? products
    : normalizeRecommendedProducts(products);
  return list.slice(0, MAX_RECOMMENDED_PRODUCTS).map((name) => {
    const meta = getProductMeta(name);
    const safeName = escapeHtml(meta.name);
    const safeDescription = escapeHtml(meta.description);
    return `
      <div class="product-card" tabindex="0" aria-label="${safeName}" data-tooltip="${safeDescription}">
        <span class="product-emoji">${meta.emoji}</span>
        <span class="product-title">${safeName}</span>
        <span class="product-tooltip" role="tooltip">${safeDescription}</span>
      </div>
    `;
  }).join("");
}

function productsTextWithEmoji(products) {
  const list = Array.isArray(products) ? products : [];
  return list.slice(0, MAX_RECOMMENDED_PRODUCTS).map((name) => {
    const meta = getProductMeta(name);
    return `${meta.emoji} ${meta.name}`;
  }).join(", ");
}

function getDefaultProductsForBottleneck(bottleneck) {
  const map = {
    "Falta de estructura digital de admisiones": [
      "CRM SuperLeads | Básico",
      "Optimización de Puntos de Contacto | Avanzado"
    ],
    "Baja cantidad de citas": [
      "CRM SuperLeads | Avanzado",
      "Seguimiento Comercial | Sesión 90 min"
    ],
    "Falta de prospectos": [
      "Campañas Integrales de Generación de Demanda | Avanzado",
      "CRM SuperLeads | Básico"
    ],
    "Baja tasa de cierre en la cita": [
      "Taller Inscripción es Cuestión de Ventas | Por participante",
      "Seguimiento Comercial | Sesión 90 min"
    ],
    "Baja conversión de lead a inscrito": [
      "Dirección Estratégica del Sistema | Avanzado",
      "CRM SuperLeads | Avanzado"
    ],
    "Hallazgo estructural": [
      "Dirección Estratégica del Sistema | Avanzado",
      "Dirección Estratégica del Sistema | Básico"
    ]
  };
  return map[bottleneck] || [
    "Dirección Estratégica del Sistema | Básico",
    "CRM SuperLeads | Básico"
  ];
}

function shouldUseThreeProducts(context, normalized) {
  if (context && context.forceThree === true) return true;
  const highComplexityBottleneck = context && (
    context.bottleneck === "Baja cantidad de citas" ||
    context.bottleneck === "Falta de estructura digital de admisiones" ||
    context.bottleneck === "Baja conversión de lead a inscrito"
  );
  return Boolean(highComplexityBottleneck && normalized.length >= 3);
}

function rankCandidates(candidates) {
  const withScore = candidates.map((c) => {
    const score = (c.severity * 0.4) + (c.moneyCloseness * 0.25) + (c.evidenceQuality * 0.2) + (c.actionability * 0.15);
    return { ...c, score };
  });

  withScore.sort((a, b) => b.score - a.score);

  const unique = [];
  const seen = new Set();
  withScore.forEach((c) => {
    if (!seen.has(c.bottleneck)) {
      seen.add(c.bottleneck);
      unique.push(c);
    }
  });

  return unique;
}

function renderResults() {
  const metrics = state.metrics;
  const result = state.diagnosticResult;
  if (!metrics || !result) return;

  updateResultsBranding();
  updateDiagnosticNote(metrics, result);
  renderFunnel(metrics);
  renderFlow(result.principal);
  renderFindings(result);
}

function updateResultsBranding() {
  const institutionName = (state.basicData.institutionName || "").trim();
  const label = institutionName
    ? `Reporte de Rayos X para ${institutionName}`
    : "Reporte de Rayos X para su institución";

  if (refs.resultsTitle) {
    refs.resultsTitle.textContent = label;
  }
  if (refs.resultsClosingTitle) {
    refs.resultsClosingTitle.textContent = label;
  }
}

function updateDiagnosticNote(metrics, result) {
  const notes = Array.isArray(metrics.funnel_notes) && metrics.funnel_notes.length
    ? ` Ajustes de consistencia aplicados: ${metrics.funnel_notes.length}.`
    : "";
  refs.diagnosticNote.textContent = `${result.status}. Tus respuestas nos permiten encontrar el cuello más probable del sistema.${notes}`;
}

function renderFunnel(metrics) {
  const rows = getFunnelRowsFromMetrics(metrics);
  const worstLabel = getWorstFunnelLabel(metrics);

  updateFunnelInsight(metrics);
  refs.funnelVisual.innerHTML = "";
  funnelAnimationToken += 1;
  const token = funnelAnimationToken;
  const reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const domRows = [];

  rows.forEach((row, index) => {
    const rowEl = document.createElement("div");
    rowEl.className = "funnel-row";

    const head = document.createElement("div");
    head.className = "funnel-head";
    const labelEl = document.createElement("span");
    labelEl.textContent = row.label;
    const valueEl = document.createElement("span");
    valueEl.textContent = Number.isFinite(row.value) ? "0" : safeNum(row.value);
    head.appendChild(labelEl);
    head.appendChild(valueEl);

    const track = document.createElement("div");
    track.className = "funnel-track is-editable";
    track.dataset.funnelIndex = String(index);
    track.setAttribute("role", "slider");
    track.setAttribute("aria-label", `Ajustar ${row.label}`);
    track.setAttribute("aria-valuemin", "0");
    track.setAttribute("aria-valuenow", safeNum(row.value));

    const fill = document.createElement("div");
    fill.className = "funnel-fill";
    fill.style.width = "0%";

    track.appendChild(fill);
    rowEl.appendChild(head);
    rowEl.appendChild(track);
    refs.funnelVisual.appendChild(rowEl);
    domRows.push({ rowEl, valueEl, track, fill });

    track.addEventListener("pointerdown", (event) => {
      beginFunnelDrag(event, index, domRows);
    });
  });

  updateFunnelDom(domRows, rows, worstLabel, {
    animate: !reduceMotion,
    token
  });
}

function animateCounter(element, targetValue, duration, token) {
  if (!Number.isFinite(targetValue)) {
    element.textContent = safeNum(targetValue);
    return;
  }

  const startTime = performance.now();

  const tick = (now) => {
    if (token !== funnelAnimationToken) return;
    const progress = Math.min(1, (now - startTime) / duration);
    const eased = 1 - Math.pow(1 - progress, 3);
    element.textContent = safeNum(targetValue * eased);
    if (progress < 1) {
      requestAnimationFrame(tick);
      return;
    }
    element.textContent = safeNum(targetValue);
  };

  requestAnimationFrame(tick);
}

function getFunnelRowsFromMetrics(metrics) {
  return [
    { key: "leads", label: "Leads", value: numericOrZero(metrics.leads) },
    { key: "contacted", label: "Contactados", value: numericOrZero(metrics.contacted) },
    { key: "appointments", label: "Citas", value: numericOrZero(metrics.appointments) },
    { key: "attended", label: "Asistieron", value: numericOrZero(metrics.attended) },
    { key: "enrolled", label: "Inscritos", value: numericOrZero(metrics.enrolled) }
  ];
}

function getWorstFunnelLabel(metrics) {
  const drops = [
    { key: "lead_to_contact_rate", value: metrics.lead_to_contact_rate, label: "Contactados" },
    { key: "contacted_to_appointment_rate", value: metrics.contacted_to_appointment_rate, label: "Citas" },
    { key: "appointment_to_attended_rate", value: metrics.appointment_to_attended_rate, label: "Asistieron" },
    { key: "attended_to_enrolled_rate", value: metrics.attended_to_enrolled_rate, label: "Inscritos" }
  ].filter((d) => Number.isFinite(d.value));

  const worst = metrics.break_stage && metrics.break_stage.label
    ? metrics.break_stage
    : (drops.length ? drops.reduce((acc, cur) => (!acc || cur.value < acc.value ? cur : acc), null) : null);

  return worst ? worst.label : "";
}

function updateFunnelInsight(metrics) {
  const extraStudentsPerPoint = Number.isFinite(metrics.leads) && metrics.leads > 0
    ? roundCadence(metrics.leads * 0.01)
    : null;

  if (!refs.funnelInsight) return;
  refs.funnelInsight.innerHTML = Number.isFinite(extraStudentsPerPoint)
    ? `<strong>+1% de conversión = ${safeNum(extraStudentsPerPoint)} alumnos extra.</strong> Arrastra cada etapa para corregir el embudo y recalcular la matemática al instante.`
    : "Arrastra cada etapa para corregir el embudo. Con más dato de leads podremos estimar cuántos alumnos extra genera cada +1% de conversión.";
}

function updateFunnelDom(domRows, rows, worstLabel, options = {}) {
  const animate = options.animate !== false;
  const token = options.token || funnelAnimationToken;
  const maxVal = Math.max(...rows.map((row) => numericOrZero(row.value)), 1);

  domRows.forEach((domRow, index) => {
    const row = rows[index];
    const targetWidth = row.value > 0
      ? Math.max(5, Math.round((numericOrZero(row.value) / maxVal) * 100))
      : 0;

    domRow.rowEl.classList.toggle("break-point", row.label === worstLabel);
    domRow.track.setAttribute("aria-valuenow", safeNum(row.value));

    if (!animate) {
      domRow.fill.style.width = `${targetWidth}%`;
      domRow.valueEl.textContent = safeNum(row.value);
      return;
    }

    const delay = 100 + (index * 140);
    setTimeout(() => {
      if (token !== funnelAnimationToken) return;
      domRow.fill.style.width = `${targetWidth}%`;
      animateCounter(domRow.valueEl, row.value, 680, token);
    }, delay);
  });
}

function beginFunnelDrag(event, index, domRows) {
  if (!state.metrics) return;
  event.preventDefault();

  const draft = getFunnelRowsFromMetrics(state.metrics).map((row) => ({ ...row }));
  const track = domRows[index].track;
  const pointerId = event.pointerId;

  if (track.setPointerCapture) {
    track.setPointerCapture(pointerId);
  }

  activeFunnelDrag = { index, domRows, draft, pointerId };
  applyFunnelPointerPosition(event.clientX);

  const onMove = (moveEvent) => {
    if (!activeFunnelDrag || moveEvent.pointerId !== pointerId) return;
    applyFunnelPointerPosition(moveEvent.clientX);
  };

  const onEnd = (endEvent) => {
    if (!activeFunnelDrag || endEvent.pointerId !== pointerId) return;
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerup", onEnd);
    window.removeEventListener("pointercancel", onEnd);
    finalizeFunnelDrag();
  };

  window.addEventListener("pointermove", onMove);
  window.addEventListener("pointerup", onEnd);
  window.addEventListener("pointercancel", onEnd);
}

function applyFunnelPointerPosition(clientX) {
  if (!activeFunnelDrag) return;
  const { index, domRows, draft } = activeFunnelDrag;
  const track = domRows[index].track;
  const rect = track.getBoundingClientRect();
  const ratioRaw = rect.width > 0 ? (clientX - rect.left) / rect.width : 0;
  const ratio = Math.max(0, Math.min(1, ratioRaw));

  const prevValue = index === 0 ? getEditableLeadUpperBound(draft) : draft[index - 1].value;
  const nextValue = index === draft.length - 1 ? 0 : draft[index + 1].value;
  const min = Math.min(prevValue, nextValue);
  const max = Math.max(prevValue, nextValue);
  draft[index].value = roundCadence(min + ((max - min) * ratio));

  for (let i = index + 1; i < draft.length; i += 1) {
    draft[i].value = Math.min(draft[i].value, draft[i - 1].value);
  }
  for (let i = index - 1; i >= 0; i -= 1) {
    draft[i].value = Math.max(draft[i].value, draft[i + 1].value);
  }

  syncFunnelDraftToState(draft);
  updateFunnelInsight(state.metrics);
  updateFunnelDom(domRows, draft, getWorstFunnelLabel(state.metrics), { animate: false });
}

function finalizeFunnelDrag() {
  if (!activeFunnelDrag) return;
  activeFunnelDrag = null;
  state.diagnosticResult = computeDiagnostic(state.metrics);
  updateDiagnosticNote(state.metrics, state.diagnosticResult);
  renderFlow(state.diagnosticResult.principal);
  renderFindings(state.diagnosticResult);
  saveState();
}

function getEditableLeadUpperBound(draft) {
  const currentLead = numericOrZero(draft[0] && draft[0].value);
  const capacityBased = numericOrZero(state.metrics && state.metrics.capacity_available) + numericOrZero(state.metrics && state.metrics.currentStudents);
  const targetBased = numericOrZero(state.metrics && state.metrics.targetNew) * 4;
  return Math.max(currentLead * 2, capacityBased, targetBased, numericOrZero(draft[1] && draft[1].value), 100);
}

function syncFunnelDraftToState(draft) {
  const values = Object.fromEntries(draft.map((row) => [row.key, roundCadence(row.value)]));
  state.responses.q6 = values.leads;
  state.leadCadence = {
    daily: roundCadence(values.leads / DAYS_PER_MONTH),
    monthly: values.leads,
    yearly: roundCadence((values.leads / DAYS_PER_MONTH) * DAYS_PER_YEAR)
  };
  state.responses.q7 = values.leads > 0 ? roundCadence((values.contacted / values.leads) * 100) : 0;
  state.responses.q8 = values.contacted > 0 ? roundCadence((values.appointments / values.contacted) * 100) : 0;
  state.responses.q9 = values.appointments > 0 ? roundCadence((values.attended / values.appointments) * 100) : 0;
  state.responses.q10 = values.enrolled;
  state.metrics = computeMetrics();
}

function renderFlow(principal) {
  refs.flowChain.innerHTML = "";
  const nodes = [
    { title: "Problema detectado", content: principal.bottleneck, accent: "problem" },
    { title: "Causa raíz", content: principal.causeRoot, accent: "cause" },
    { title: "Solución correcta", content: principal.solution, accent: "solution" },
    { title: "Producto(s) SuperLeads", content: principal.products, accent: "products", isProducts: true }
  ];

  nodes.forEach((node, idx) => {
    const box = document.createElement("div");
    box.className = `flow-box flow-box-${node.accent}`;

    const title = document.createElement("strong");
    title.className = "flow-box-title";
    title.textContent = node.title;

    const body = document.createElement("div");
    body.className = "flow-box-body";
    if (node.isProducts) {
      body.classList.add("flow-box-products");
      body.innerHTML = renderProductsContainersHtml(node.content);
    } else {
      const paragraph = document.createElement("p");
      paragraph.textContent = node.content;
      body.appendChild(paragraph);
    }

    box.appendChild(title);
    box.appendChild(body);
    refs.flowChain.appendChild(box);

    if (idx < nodes.length - 1) {
      const arrow = document.createElement("div");
      arrow.className = "flow-arrow";
      arrow.innerHTML = '<span class="flow-arrow-line"></span><span class="flow-arrow-head"></span>';
      refs.flowChain.appendChild(arrow);
    }
  });
}

function renderFindings(result) {
  refs.findingsGrid.innerHTML = "";

  const items = [result.principal, ...result.secondary].slice(0, 3);

  items.forEach((item, idx) => {
    const card = document.createElement("article");
    card.className = `finding-card reveal-${Math.min(idx + 1, 3)}`;

    const badges = document.createElement("div");
    badges.className = "badges";
    const badgeButtons = [];

    const statusBadge = document.createElement("button");
    statusBadge.type = "button";
    statusBadge.className = `badge ${idx === 0 ? "primary" : ""}`;
    statusBadge.textContent = idx === 0 ? "Principal" : "Secundario";
    statusBadge.dataset.tag = idx === 0 ? "principal" : "secundario";
    badges.appendChild(statusBadge);
    badgeButtons.push(statusBadge);

    item.tags.forEach((tag) => {
      const tagEl = document.createElement("button");
      tagEl.type = "button";
      tagEl.className = `badge ${tag.toLowerCase().includes("estructural") ? "structural" : ""}`;
      tagEl.textContent = tag;
      tagEl.dataset.tag = normalizeTag(tag);
      badges.appendChild(tagEl);
      badgeButtons.push(tagEl);
    });

    const evidenceLines = item.evidence.map((line) => `<li>${line}</li>`).join("");
    const products = renderProductsContainersHtml(item.products);

    const guidance = document.createElement("p");
    guidance.className = "tag-guidance";
    guidance.textContent = "Etiqueta activa: vista general del hallazgo.";

    const sections = document.createElement("div");
    sections.className = "finding-sections";
    sections.innerHTML = `
      <h4>${item.bottleneck}</h4>
      <div class="finding-section section-problema">
        <p><strong>Problema detectado:</strong> ${item.visibleIssue}</p>
      </div>
      <div class="finding-section section-evidencia">
        <p><strong>Qué vimos en sus respuestas:</strong></p>
        <ul class="products">${evidenceLines}</ul>
        <p><strong>Por qué creemos esto:</strong> ${item.evidenceQuality >= 75 ? "La evidencia es consistente entre respuestas y métricas del embudo." : "La evidencia existe, pero todavía conviene robustecer datos."}</p>
      </div>
      <div class="finding-section section-causa">
        <p><strong>Causa raíz:</strong> ${item.causeRoot}</p>
      </div>
      <div class="finding-section section-impacto">
        <p><strong>Qué impacta en su crecimiento:</strong> ${item.impact}</p>
      </div>
      <div class="finding-section section-solucion">
        <p><strong>Solución correcta:</strong> ${item.solution}</p>
      </div>
      <div class="finding-section section-productos">
        <p><strong>Productos SuperLeads recomendados:</strong></p>
        <div class="products-grid">${products}</div>
      </div>
    `;

    card.appendChild(badges);
    card.appendChild(guidance);
    card.appendChild(sections);

    const sectionNodes = Array.from(card.querySelectorAll(".finding-section"));
    const applyTagFocus = (tagKey) => {
      const targetSelector = tagToSectionSelector(tagKey);
      const guidanceText = tagToGuidanceText(tagKey, item);
      guidance.textContent = guidanceText;

      badgeButtons.forEach((b) => b.classList.toggle("active", b.dataset.tag === tagKey));

      if (!targetSelector) {
        sectionNodes.forEach((section) => section.classList.remove("is-muted", "is-focused"));
        return;
      }

      sectionNodes.forEach((section) => {
        const focused = section.matches(targetSelector);
        section.classList.toggle("is-focused", focused);
        section.classList.toggle("is-muted", !focused);
      });
    };

    badgeButtons.forEach((btn) => {
      btn.addEventListener("click", () => applyTagFocus(btn.dataset.tag || ""));
    });

    applyTagFocus("principal");
    refs.findingsGrid.appendChild(card);
  });
}

function normalizeTag(tag) {
  const lower = String(tag || "").toLowerCase();
  if (lower.includes("causa")) return "causa";
  if (lower.includes("base")) return "base";
  if (lower.includes("estructural")) return "estructural";
  if (lower.includes("visible")) return "visible";
  if (lower.includes("principal")) return "principal";
  if (lower.includes("secundario")) return "secundario";
  return "general";
}

function tagToSectionSelector(tagKey) {
  const map = {
    principal: ".section-problema",
    secundario: ".section-impacto",
    visible: ".section-problema",
    causa: ".section-causa",
    base: ".section-productos",
    estructural: ".section-impacto"
  };
  return map[tagKey] || null;
}

function tagToGuidanceText(tagKey, item) {
  const totalProducts = Array.isArray(item.products) ? item.products.length : 0;
  const map = {
    principal: "Etiqueta activa: este es el frente que más dinero destraba si se corrige primero.",
    secundario: "Etiqueta activa: este frente acompaña la mejora del cuello principal.",
    visible: "Etiqueta activa: aquí está el síntoma que hoy sí se ve en la operación.",
    causa: "Etiqueta activa: aquí está la causa raíz que está provocando la fuga.",
    base: `Etiqueta activa: esta base operativa se vuelve prioridad. Productos sugeridos: ${totalProducts}.`,
    estructural: "Etiqueta activa: hay factores estructurales que requieren dirección estratégica, no solo software.",
    general: "Etiqueta activa: vista general del hallazgo."
  };
  return map[tagKey] || map.general;
}

function animateQuestionCard() {
  const card = document.querySelector(".question-card");
  if (!card) return;
  card.classList.remove("slide-in");
  // Force reflow to replay animation.
  void card.offsetWidth;
  card.classList.add("slide-in");
}

function pulseProgress() {
  if (!refs.progressBar) return;
  refs.progressBar.classList.remove("animate");
  void refs.progressBar.offsetWidth;
  refs.progressBar.classList.add("animate");
}

function startConstanzaEmojiLoop() {
  if (!refs.constanzaWhatsappEmoji) return;
  refs.constanzaWhatsappEmoji.textContent = CONSTANZA_BUTTON_EMOJIS[constanzaEmojiIndex];
  if (constanzaEmojiInterval) {
    clearInterval(constanzaEmojiInterval);
  }
  constanzaEmojiInterval = window.setInterval(() => {
    constanzaEmojiIndex = (constanzaEmojiIndex + 1) % CONSTANZA_BUTTON_EMOJIS.length;
    refs.constanzaWhatsappEmoji.textContent = CONSTANZA_BUTTON_EMOJIS[constanzaEmojiIndex];
  }, 10000);
}

async function generateAndDownloadReport(isAutomatic) {
  try {
    await generatePremiumPrintReport(isAutomatic);
    state.pdfAutoDownloaded = true;
    saveState();
  } catch (_error) {
    await generateLegacyPdf(isAutomatic);
  }
}

async function generatePremiumPrintReport(_isAutomatic) {
  const payload = buildPremiumReportPayload();
  await openPremiumPrintFrame(payload);
}

function buildPremiumReportPayload() {
  const metrics = state.metrics || {};
  const diagnostic = state.diagnosticResult || {};
  const cost = computeCostOfInaction(metrics);
  const reportGeneratedAt = new Date();
  const reportStamp = formatMexicoCitySeal(reportGeneratedAt);

  return {
    filename: getReportFilename(),
    stamp: reportStamp,
    generatedAtIso: reportGeneratedAt.toISOString(),
    basicData: { ...state.basicData },
    metrics,
    diagnostic,
    cost,
    questions: questions.map((question, index) => ({
      index: index + 1,
      stage: stages[question.stage],
      label: question.label,
      answer: getAnswerLabel(question, state.responses[question.id])
    }))
  };
}

function openPremiumPrintFrame(payload) {
  cleanupPremiumPrintFrame();

  return new Promise((resolve, reject) => {
    const iframe = document.createElement("iframe");
    const channel = `premium-print-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    let settled = false;
    let timeoutId = null;
    premiumPrintIframe = iframe;
    iframe.className = "print-frame";
    iframe.setAttribute("aria-hidden", "true");
    iframe.srcdoc = buildPremiumReportDocument(payload, channel);
    document.body.appendChild(iframe);

    const fail = (error) => {
      if (settled) return;
      settled = true;
      if (timeoutId) clearTimeout(timeoutId);
      window.removeEventListener("message", onMessage);
      cleanupPremiumPrintFrame();
      reject(error);
    };

    const succeed = () => {
      if (settled) return;
      settled = true;
      if (timeoutId) clearTimeout(timeoutId);
      window.removeEventListener("message", onMessage);
      try {
        iframe.contentWindow.focus();
        iframe.contentWindow.print();
      } catch (error) {
        cleanupPremiumPrintFrame();
        reject(error);
        return;
      }

      const cleanup = () => {
        cleanupPremiumPrintFrame();
      };

      try {
        iframe.contentWindow.addEventListener("afterprint", cleanup, { once: true });
      } catch (_error) {
        window.setTimeout(cleanup, 2500);
      }
      window.setTimeout(cleanup, 2500);
      resolve();
    };

    const onMessage = (event) => {
      if (!event.data || event.data.channel !== channel) return;
      if (event.data.type === "premium-report-ready") {
        succeed();
        return;
      }
      if (event.data.type === "premium-report-error") {
        fail(new Error(event.data.message || "No se pudo preparar el reporte premium."));
      }
    };

    window.addEventListener("message", onMessage);

    timeoutId = window.setTimeout(() => {
      fail(new Error("Tiempo agotado al preparar el reporte premium."));
    }, 18000);
  });
}

function cleanupPremiumPrintFrame() {
  if (premiumPrintIframe && premiumPrintIframe.parentNode) {
    premiumPrintIframe.parentNode.removeChild(premiumPrintIframe);
  }
  premiumPrintIframe = null;
}

function buildPremiumReportDocument(payload, channel) {
  const title = payload.basicData.institutionName
    ? `Reporte de Rayos X para ${payload.basicData.institutionName}`
    : "Reporte de Rayos X para su institución";
  const coverStatus = payload.diagnostic.status || "Diagnóstico preliminar";
  const answersHtml = payload.questions.map((item) => `
    <article class="qa-item">
      <span class="qa-meta">${escapeHtml(item.stage)} · Pregunta ${item.index}</span>
      <h4>${escapeHtml(item.label)}</h4>
      <p>${escapeHtml(item.answer)}</p>
    </article>
  `).join("");
  const findingsHtml = buildPremiumFindingsHtml(payload.diagnostic);
  const secondaryHtml = Array.isArray(payload.diagnostic.secondary) && payload.diagnostic.secondary.length
    ? payload.diagnostic.secondary.map((item) => `
      <article class="secondary-card">
        <div class="secondary-head">
          <span class="eyebrow">Secundario</span>
          <h4>${escapeHtml(item.bottleneck)}</h4>
        </div>
        <p><strong>Causa raíz:</strong> ${escapeHtml(item.causeRoot)}</p>
        <p><strong>Solución:</strong> ${escapeHtml(item.solution)}</p>
      </article>
    `).join("")
    : '<p class="muted">No aparecieron cuellos secundarios en este corte.</p>';

  return `<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(payload.filename)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap" rel="stylesheet">
  <style>${buildPremiumReportStyles()}</style>
  <script>
    window.PagedConfig = { auto: false };
    window.__premiumPrintChannel = ${JSON.stringify(channel)};
    function premiumNotify(type, message) {
      parent.postMessage({ channel: window.__premiumPrintChannel, type, message }, "*");
    }
    window.addEventListener("load", () => {
      const start = () => {
        if (!window.PagedPolyfill || !window.PagedPolyfill.preview) {
          window.setTimeout(start, 40);
          return;
        }
        window.PagedPolyfill.preview()
          .then(() => premiumNotify("premium-report-ready"))
          .catch((error) => premiumNotify("premium-report-error", error && error.message ? error.message : "Falló Paged.js"));
      };
      start();
    });
  </script>
  <script src="${PAGED_JS_POLYFILL_URL}"></script>
</head>
<body>
  <div class="print-running-header">
    <img src="${SUPERLEADS_LOGO_URL}" alt="SuperLeads">
    <span>${escapeHtml(title)}</span>
  </div>
  <div class="print-running-footer">
    <span>SuperLeads · ${escapeHtml(payload.stamp.full)} · CDMX</span>
    <span class="page-counter"></span>
  </div>

  <main class="report">
    <section class="report-page cover-page">
      <div class="cover-logo">
        <img src="${SUPERLEADS_LOGO_URL}" alt="SuperLeads">
      </div>
      <div class="cover-copy">
        <span class="eyebrow">Reporte editorial premium</span>
        <h1>${escapeHtml(title)}</h1>
        <p class="lede">Radiografía comercial del sistema de inscripciones con evidencia, cuello principal, causa raíz, solución correcta y productos exactos de SuperLeads.</p>
      </div>
      <div class="hero-band">
        <div class="hero-pill">
          <span>Diagnóstico</span>
          <strong>${escapeHtml(coverStatus)}</strong>
        </div>
        <div class="hero-pill">
          <span>Sello de emisión</span>
          <strong>${escapeHtml(payload.stamp.full)}</strong>
        </div>
        <div class="hero-pill">
          <span>Institución</span>
          <strong>${escapeHtml(payload.basicData.institutionName || "Sin dato")}</strong>
        </div>
      </div>
    </section>

    <section class="report-page summary-page">
      <div class="section-head">
        <span class="eyebrow">Resumen ejecutivo</span>
        <h2>Esto encontramos en su sistema de inscripciones</h2>
      </div>
      <div class="kpi-grid">
        ${buildPremiumSummaryCards(payload)}
      </div>
      <div class="narrative-card">
        <div class="narrative-step">Respuesta</div>
        <div class="narrative-arrow">→</div>
        <div class="narrative-step">Evidencia</div>
        <div class="narrative-arrow">→</div>
        <div class="narrative-step">Cuello</div>
        <div class="narrative-arrow">→</div>
        <div class="narrative-step">Causa raíz</div>
        <div class="narrative-arrow">→</div>
        <div class="narrative-step">Solución</div>
        <div class="narrative-arrow">→</div>
        <div class="narrative-step">Producto SuperLeads</div>
      </div>
      <div class="basic-grid">
        ${buildPremiumBasicData(payload)}
      </div>
    </section>

    <section class="report-page funnel-page">
      <div class="section-head">
        <span class="eyebrow">Embudo reconstruido</span>
        <h2>Visual premium del sistema de admisiones</h2>
      </div>
      <div class="visual-card">
        ${buildPremiumFunnelSvg(payload.metrics)}
      </div>
      <div class="metrics-grid">
        ${buildPremiumMetricCards(payload.metrics, payload.cost)}
      </div>
    </section>

    <section class="report-page findings-page">
      <div class="section-head">
        <span class="eyebrow">Hallazgos priorizados</span>
        <h2>Qué explica la fuga comercial y qué la corrige</h2>
      </div>
      <div class="findings-stack">
        ${findingsHtml}
      </div>
    </section>

    <section class="report-page cost-page">
      <div class="section-head">
        <span class="eyebrow">Costo de no hacer nada</span>
        <h2>La oportunidad comercial que hoy está quedando sobre la mesa</h2>
      </div>
      <div class="impact-hero">
        <span>Impacto anualizado estimado</span>
        <strong>${escapeHtml(money(payload.cost.annualImpact))}</strong>
        <p>${escapeHtml(payload.cost.executiveText)}</p>
      </div>
      <div class="impact-grid">
        ${buildPremiumImpactCards(payload.cost)}
      </div>
      <div class="visual-card">
        ${buildPremiumImpactSvg(payload.cost)}
      </div>
    </section>

    <section class="report-page appendix-page">
      <div class="section-head">
        <span class="eyebrow">Detalle completo</span>
        <h2>Preguntas y respuestas del diagnóstico</h2>
      </div>
      <div class="qa-grid">
        ${answersHtml}
      </div>
    </section>

    <section class="report-page close-page">
      <div class="section-head">
        <span class="eyebrow">Cuellos secundarios</span>
        <h2>Lo que también conviene atender</h2>
      </div>
      <div class="secondary-grid">${secondaryHtml}</div>
      <div class="closing-statement">
        <span>Este reporte busca claridad comercial, no perfección contable.</span>
      </div>
      <div class="constanza-card">
        <img src="${CONSTANZA_PHOTO_URL}" alt="Constanza">
        <div>
          <span class="eyebrow">Siguiente paso</span>
          <h3>Constanza puede acompañar la ejecución</h3>
          <p>Si quieren convertir este diagnóstico en un plan claro y accionable, el siguiente paso es abrir la conversación con Constanza y continuar el proceso.</p>
          <a href="https://wa.me/5218711185888?text=Hola" target="_blank" rel="noopener noreferrer">💬 Escribir a Constanza por WhatsApp</a>
        </div>
      </div>
    </section>
  </main>
</body>
</html>`;
}

function buildPremiumSummaryCards(payload) {
  const principal = payload.diagnostic.principal || {};
  const cards = [
    {
      label: "Cuello principal",
      value: principal.bottleneck || "Sin definir",
      body: principal.visibleIssue || "Sin síntoma priorizado"
    },
    {
      label: "Causa raíz",
      value: principal.causeRoot || "Sin definir",
      body: `Confianza del hallazgo: ${pct(payload.metrics.confidence_score)}`
    },
    {
      label: "Productos",
      value: String((principal.products || []).length || 0),
      body: productsTextWithEmoji(principal.products || [])
    }
  ];

  return cards.map((card) => `
    <article class="kpi-card">
      <span>${escapeHtml(card.label)}</span>
      <strong>${escapeHtml(card.value)}</strong>
      <p>${escapeHtml(card.body)}</p>
    </article>
  `).join("");
}

function buildPremiumBasicData(payload) {
  const items = [
    ["URL institucional", payload.basicData.institutionUrl || "Sin dato"],
    ["Nombre institución", payload.basicData.institutionName || "Sin dato"],
    ["Años de existir", payload.basicData.yearsOperating || "Sin dato"],
    ["Nombre completo", payload.basicData.fullName || "Sin dato"],
    ["Celular", payload.basicData.phone || "Sin dato"],
    ["Correo", payload.basicData.email || "Sin dato"]
  ];

  return items.map(([label, value]) => `
    <div class="basic-item">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `).join("");
}

function buildPremiumFunnelSvg(metrics) {
  const rows = getFunnelRowsFromMetrics(metrics);
  const max = Math.max(...rows.map((row) => numericOrZero(row.value)), 1);
  const highlight = getWorstFunnelLabel(metrics);
  const width = 920;
  const barX = 150;
  const barWidth = 720;
  const barHeight = 36;
  const rowGap = 74;
  const startY = 34;
  const totalHeight = startY + (rows.length * rowGap);

  const content = rows.map((row, index) => {
    const y = startY + (index * rowGap);
    const fill = Math.max(10, (numericOrZero(row.value) / max) * barWidth);
    const isHighlight = row.label === highlight;
    return `
      <text x="0" y="${y + 24}" class="svg-label">${escapeHtml(row.label)}</text>
      <rect x="${barX}" y="${y}" width="${barWidth}" height="${barHeight}" rx="18" fill="#161616" stroke="#2a2a2a" />
      <rect x="${barX}" y="${y}" width="${fill}" height="${barHeight}" rx="18" fill="${isHighlight ? "#2454ff" : "url(#funnelGradient)"}" />
      <text x="${barX + barWidth}" y="${y + 24}" text-anchor="end" class="svg-value">${escapeHtml(safeNum(row.value))}</text>
      ${isHighlight ? `<text x="${barX}" y="${y + 56}" class="svg-note">Ruptura dominante</text>` : ""}
    `;
  }).join("");

  return `
    <svg class="report-svg" viewBox="0 0 ${width} ${totalHeight}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Embudo reconstruido">
      <defs>
        <linearGradient id="funnelGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#9e9e9e"/>
          <stop offset="100%" stop-color="#ffffff"/>
        </linearGradient>
      </defs>
      ${content}
    </svg>
  `;
}

function buildPremiumMetricCards(metrics, cost) {
  const items = [
    ["Lead → Contactado", pct(metrics.lead_to_contact_rate)],
    ["Contactado → Cita", pct(metrics.contacted_to_appointment_rate)],
    ["Cita → Asistencia", pct(metrics.appointment_to_attended_rate)],
    ["Asistencia → Inscripción", pct(metrics.attended_to_enrolled_rate)],
    ["Lead → Inscrito", pct(metrics.lead_to_enrolled_rate)],
    ["+1% de conversión", `${safeNum(cost.extraStudentsPerPoint)} alumnos extra`],
    ["Valor por alumno", money(metrics.valuePerSeat || 0)],
    ["Capacidad disponible", safeNum(metrics.capacity_available)]
  ];

  return items.map(([label, value]) => `
    <article class="metric-card">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </article>
  `).join("");
}

function buildPremiumFindingsHtml(diagnostic) {
  const items = diagnostic && Array.isArray(diagnostic.all) ? diagnostic.all.slice(0, 3) : [];
  return items.map((item, index) => `
    <article class="finding-print-card ${index === 0 ? "finding-print-card-main" : ""}">
      <div class="finding-print-head">
        <div class="badge-row">
          <span class="print-badge ${index === 0 ? "print-badge-main" : ""}">${index === 0 ? "Principal" : "Secundario"}</span>
          ${(item.tags || []).map((tag) => `<span class="print-badge">${escapeHtml(tag)}</span>`).join("")}
        </div>
        <h3>${escapeHtml(item.bottleneck)}</h3>
      </div>
      <div class="finding-print-grid">
        <div class="finding-block">
          <span>Problema detectado</span>
          <p>${escapeHtml(item.visibleIssue)}</p>
        </div>
        <div class="finding-block">
          <span>Causa raíz</span>
          <p>${escapeHtml(item.causeRoot)}</p>
        </div>
        <div class="finding-block">
          <span>Qué impacta en el crecimiento</span>
          <p>${escapeHtml(item.impact)}</p>
        </div>
        <div class="finding-block">
          <span>Solución correcta</span>
          <p>${escapeHtml(item.solution)}</p>
        </div>
      </div>
      <div class="evidence-list">
        ${(item.evidence || []).map((line) => `<div class="evidence-item">${escapeHtml(line)}</div>`).join("")}
      </div>
      <div class="print-products-grid">
        ${buildPremiumProductCards(item.products)}
      </div>
    </article>
  `).join("");
}

function buildPremiumProductCards(products) {
  const list = normalizeRecommendedProducts(products || []);
  return list.slice(0, MAX_RECOMMENDED_PRODUCTS).map((productName) => {
    const meta = getProductMeta(productName);
    return `
      <article class="print-product-card">
        <span class="print-product-emoji">${escapeHtml(meta.emoji)}</span>
        <div>
          <h4>${escapeHtml(meta.name)}</h4>
          <p>${escapeHtml(meta.description)}</p>
        </div>
      </article>
    `;
  }).join("");
}

function buildPremiumImpactCards(cost) {
  const items = [
    ["Brecha estimada", safeNum(cost.enrollmentGap)],
    ["Capacidad ociosa", safeNum(cost.idleSeats)],
    ["Estudiantes en riesgo", safeNum(cost.lostStudentsEquivalent)],
    ["Costo total", money(cost.totalImpact)],
    ["Impacto mensual", money(cost.monthlyImpact)],
    ["Impacto a 18 meses", money(cost.eighteenMonthImpact)]
  ];

  return items.map(([label, value]) => `
    <article class="impact-card">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </article>
  `).join("");
}

function buildPremiumImpactSvg(cost) {
  const scenarios = [
    { label: "Mensual", value: numericOrZero(cost.monthlyImpact) },
    { label: "12 meses", value: numericOrZero(cost.annualImpact) },
    { label: "18 meses", value: numericOrZero(cost.eighteenMonthImpact) }
  ];
  const max = Math.max(...scenarios.map((item) => item.value), 1);
  const width = 920;
  const chartX = 180;
  const chartWidth = 680;
  const rowGap = 76;
  const startY = 36;
  const height = 280;

  const rows = scenarios.map((item, index) => {
    const y = startY + (index * rowGap);
    const fill = Math.max(10, (item.value / max) * chartWidth);
    const highlight = index === 1;
    return `
      <text x="0" y="${y + 24}" class="svg-label">${escapeHtml(item.label)}</text>
      <rect x="${chartX}" y="${y}" width="${chartWidth}" height="34" rx="17" fill="#151515" stroke="#2a2a2a"/>
      <rect x="${chartX}" y="${y}" width="${fill}" height="34" rx="17" fill="${highlight ? "#2454ff" : "#f0f0f0"}"/>
      <text x="${chartX + chartWidth}" y="${y + 24}" text-anchor="end" class="svg-value">${escapeHtml(money(item.value))}</text>
    `;
  }).join("");

  return `
    <svg class="report-svg" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Escenarios de impacto">
      ${rows}
      <text x="0" y="256" class="svg-note">+1% de conversión = ${escapeHtml(safeNum(cost.extraStudentsPerPoint))} alumnos extra · ${escapeHtml(money(cost.extraRevenuePerPoint))} en valor adicional</text>
    </svg>
  `;
}

function buildPremiumReportStyles() {
  return `
    :root {
      --bg: #020202;
      --panel: #0d0d0d;
      --panel-soft: #121212;
      --line: #252525;
      --line-strong: #343434;
      --text: #ffffff;
      --text-soft: #cfcfcf;
      --text-dim: #979797;
      --blue: #1f50ff;
      --blue-soft: #dfe7ff;
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; padding: 0; font-family: "Roboto", sans-serif; background: var(--bg); color: var(--text); }
    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .print-running-header, .print-running-footer { color: var(--text-soft); font-size: 10px; }
    .print-running-header { position: running(reportHeader); display: flex; align-items: center; justify-content: center; gap: 14px; height: 22px; }
    .print-running-header img { width: 138px; height: auto; display: block; }
    .print-running-header span { font-weight: 600; letter-spacing: 0.02em; }
    .print-running-footer { position: running(reportFooter); display: flex; justify-content: space-between; align-items: center; gap: 14px; height: 16px; width: 100%; }
    .page-counter::after { content: "Página " counter(page) " de " counter(pages); }
    @page {
      size: A4;
      margin: 24mm 16mm 18mm;
      @top-center { content: element(reportHeader); }
      @bottom-center { content: element(reportFooter); }
    }
    h1, h2, h3, h4, p { margin: 0; }
    .report { width: 100%; }
    .report-page { break-before: page; page-break-before: always; min-height: 246mm; display: grid; align-content: start; gap: 18px; }
    .report-page:first-child { break-before: auto; page-break-before: auto; }
    .cover-page { min-height: 250mm; align-content: center; gap: 28px; }
    .cover-logo { display: flex; justify-content: center; }
    .cover-logo img { width: 260px; display: block; }
    .cover-copy { text-align: center; display: grid; gap: 14px; }
    .cover-copy h1 { font-size: 30px; line-height: 1.06; letter-spacing: -0.03em; }
    .lede { max-width: 620px; margin: 0 auto; color: var(--text-soft); font-size: 13px; line-height: 1.55; }
    .eyebrow { display: inline-flex; width: fit-content; padding: 6px 12px; border-radius: 999px; background: #ffffff; color: #000000; font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; }
    .section-head { display: grid; gap: 10px; }
    .section-head h2 { font-size: 25px; line-height: 1.08; letter-spacing: -0.03em; }
    .hero-band, .basic-grid, .kpi-grid, .metrics-grid, .impact-grid, .secondary-grid { display: grid; gap: 12px; }
    .hero-band { grid-template-columns: repeat(3, 1fr); }
    .hero-pill, .kpi-card, .basic-item, .metric-card, .impact-card, .secondary-card, .qa-item, .finding-print-card, .visual-card, .closing-statement, .narrative-card { background: var(--panel); border: 1px solid var(--line); border-radius: 18px; }
    .hero-pill { padding: 16px; display: grid; gap: 8px; }
    .hero-pill span, .kpi-card span, .basic-item span, .metric-card span, .impact-card span, .finding-block span { color: var(--text-dim); font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700; }
    .hero-pill strong, .basic-item strong, .impact-card strong { font-size: 16px; line-height: 1.2; }
    .kpi-grid { grid-template-columns: repeat(3, 1fr); }
    .kpi-card { padding: 18px; min-height: 140px; display: grid; align-content: start; gap: 10px; }
    .kpi-card strong { font-size: 22px; line-height: 1.05; letter-spacing: -0.03em; }
    .kpi-card p { color: var(--text-soft); font-size: 12px; line-height: 1.5; }
    .narrative-card { padding: 16px 18px; display: grid; grid-template-columns: repeat(11, auto); justify-content: center; gap: 10px; align-items: center; }
    .narrative-step { padding: 8px 12px; border-radius: 999px; background: #151515; border: 1px solid #2d2d2d; font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700; }
    .narrative-arrow { color: var(--blue-soft); font-size: 18px; font-weight: 900; }
    .basic-grid { grid-template-columns: repeat(3, 1fr); }
    .basic-item, .metric-card, .impact-card { padding: 14px 16px; display: grid; gap: 8px; min-height: 82px; }
    .visual-card { padding: 18px; }
    .report-svg { width: 100%; height: auto; display: block; }
    .svg-label { fill: #e6e6e6; font-size: 15px; font-weight: 600; }
    .svg-value { fill: #ffffff; font-size: 14px; font-weight: 700; }
    .svg-note { fill: #a8beff; font-size: 12px; font-weight: 700; }
    .metrics-grid, .impact-grid, .secondary-grid { grid-template-columns: repeat(3, 1fr); }
    .metric-card strong { font-size: 19px; line-height: 1.08; }
    .findings-stack { display: grid; gap: 16px; }
    .finding-print-card { padding: 18px; display: grid; gap: 14px; }
    .finding-print-card-main { border-color: #4d67a8; box-shadow: inset 0 0 0 1px rgba(83, 116, 214, 0.35); }
    .finding-print-head { display: grid; gap: 10px; }
    .badge-row { display: flex; flex-wrap: wrap; gap: 8px; }
    .print-badge { padding: 6px 10px; border-radius: 999px; border: 1px solid var(--line-strong); color: var(--text-soft); font-size: 9px; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700; }
    .print-badge-main { background: #ffffff; color: #000000; border-color: #ffffff; }
    .finding-print-head h3 { font-size: 24px; line-height: 1.08; }
    .finding-print-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
    .finding-block { padding: 14px; background: var(--panel-soft); border-radius: 14px; border: 1px solid #1f1f1f; display: grid; gap: 8px; }
    .finding-block p { color: var(--text-soft); font-size: 12px; line-height: 1.55; }
    .evidence-list { display: grid; gap: 8px; }
    .evidence-item { padding: 10px 12px; background: #101010; border-radius: 12px; border: 1px solid #202020; color: var(--text-soft); font-size: 11px; line-height: 1.45; }
    .print-products-grid { display: grid; gap: 10px; }
    .print-product-card { display: grid; grid-template-columns: 40px 1fr; gap: 12px; padding: 14px 16px; background: linear-gradient(135deg, #1d4ef9, #1437aa); border-radius: 16px; color: #ffffff; break-inside: avoid; }
    .print-product-emoji { font-size: 22px; line-height: 1; display: flex; justify-content: center; align-items: start; padding-top: 2px; }
    .print-product-card h4 { font-size: 15px; line-height: 1.2; margin-bottom: 5px; }
    .print-product-card p { font-size: 11px; line-height: 1.5; color: #eef2ff; }
    .impact-hero { padding: 20px 22px; background: linear-gradient(135deg, #0f2f95, #1d4ef9); border-radius: 22px; display: grid; gap: 10px; }
    .impact-hero span { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700; color: #d9e3ff; }
    .impact-hero strong { font-size: 34px; line-height: 1; letter-spacing: -0.04em; }
    .impact-hero p { max-width: 620px; color: #eef2ff; font-size: 12px; line-height: 1.5; }
    .qa-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; align-items: start; }
    .qa-item { padding: 14px 16px; display: grid; gap: 8px; break-inside: avoid; }
    .qa-meta { color: var(--text-dim); font-size: 9px; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 700; }
    .qa-item h4 { font-size: 14px; line-height: 1.3; }
    .qa-item p { color: var(--text-soft); font-size: 12px; line-height: 1.5; }
    .muted { color: var(--text-soft); font-size: 12px; line-height: 1.5; }
    .closing-statement { min-height: 110px; display: flex; align-items: center; justify-content: center; text-align: center; padding: 20px 28px; }
    .closing-statement span { font-size: 18px; line-height: 1.45; font-weight: 700; max-width: 520px; }
    .constanza-card { display: grid; grid-template-columns: 124px 1fr; gap: 20px; align-items: center; padding: 20px; background: linear-gradient(180deg, #0e0e0e, #090909); border: 1px solid var(--line); border-radius: 22px; break-inside: avoid; }
    .constanza-card img { width: 124px; height: 124px; border-radius: 50%; object-fit: cover; border: 3px solid #ffffff; }
    .constanza-card h3 { font-size: 22px; line-height: 1.08; margin: 4px 0 10px; }
    .constanza-card p { color: var(--text-soft); font-size: 12px; line-height: 1.6; margin-bottom: 14px; }
    .constanza-card a { display: inline-flex; align-items: center; gap: 10px; padding: 12px 18px; border-radius: 999px; background: #56c36f; color: #ffffff; text-decoration: none; font-weight: 800; }
    .pagedjs_page { background: var(--bg); }
  `;
}

async function generateLegacyPdf(isAutomatic) {
  try {
    if (!window.jspdf || !window.jspdf.jsPDF) {
      throw new Error("jsPDF no disponible");
    }

    const filename = getReportFilename();
    const doc = new window.jspdf.jsPDF({ unit: "pt", format: "a4" });
    const page = {
      width: doc.internal.pageSize.getWidth(),
      height: doc.internal.pageSize.getHeight(),
      marginX: 52,
      marginTop: 64,
      marginBottom: 58,
      gutter: 14,
      baseline: 4,
      number: 1,
      y: 64
    };
    syncLayout(page);
    const reportGeneratedAt = new Date();
    const reportStamp = formatMexicoCitySeal(reportGeneratedAt);
    page.reportStamp = reportStamp;
    const logoAsset = await getPdfLogoAsset();
    page.logoAsset = logoAsset || null;

    const m = state.metrics || {};
    const d = state.diagnosticResult || {};
    const cost = computeCostOfInaction(m);

    prepareDarkPage(doc, page, logoAsset);
    writeCover(doc, page, d.status || "Diagnóstico preliminar");
    addPage(doc, page, logoAsset);
    writeCostPage(doc, page, cost);
    addPage(doc, page, logoAsset);

    writeSectionTitle(doc, page, "1. Datos básicos");
    writeParagraph(doc, page, `Sello de emisión CDMX: ${reportStamp.full}`);
    writeParagraph(doc, page, `URL institucional: ${state.basicData.institutionUrl || "Sin dato"}`);
    writeParagraph(doc, page, `Institución: ${state.basicData.institutionName || "Sin dato"}`);
    writeParagraph(doc, page, `Años de existir: ${state.basicData.yearsOperating || "Sin dato"}`);
    writeParagraph(doc, page, `Nombre completo: ${state.basicData.fullName || "Sin dato"}`);
    writeParagraph(doc, page, `Celular: ${state.basicData.phone || "Sin dato"}`);
    writeParagraph(doc, page, `Correo: ${state.basicData.email || "Sin dato"}`);

    writeSectionTitle(doc, page, "2. Resumen ejecutivo");
    writeParagraph(doc, page, `Cuello principal: ${d.principal ? d.principal.bottleneck : "Sin definir"}`);
    writeParagraph(doc, page, `Diagnóstico: ${d.status || "Diagnóstico preliminar"}`);
    writeParagraph(doc, page, `Narrativa: respuesta → evidencia → cuello → causa raíz → solución → producto SuperLeads`);
    drawExecutiveSnapshot(doc, page, d, cost, m);

    writeSectionTitle(doc, page, "3. Resumen del embudo");
    drawPdfFunnelChart(doc, page, m);
    drawPdfRateCards(doc, page, m);
    writeMetricRow(doc, page, "Leads", safeNum(m.leads), "Contactados", safeNum(m.contacted));
    writeMetricRow(doc, page, "Citas", safeNum(m.appointments), "Asistieron", safeNum(m.attended));
    writeMetricRow(doc, page, "Inscritos", safeNum(m.enrolled), "Capacidad disponible", safeNum(m.capacity_available));
    writeMetricRow(doc, page, "Colegiatura promedio (MXN)", money(m.averageTuition || 0), "Meses promedio por alumno", safeNum(m.averageMonths));
    writeMetricRow(doc, page, "Valor total por alumno", money(m.valuePerSeat || 0), "Suficiencia de leads", formatBool(m.lead_sufficiency));
    writeMetricRow(doc, page, "Lead→Contactado", pct(m.lead_to_contact_rate), "Lead→Cita", pct(m.lead_to_appointment_rate));
    writeMetricRow(doc, page, "Contactado→Cita", pct(m.contacted_to_appointment_rate), "Cita→Asistencia", pct(m.appointment_to_attended_rate));
    writeMetricRow(doc, page, "Asistencia→Inscripción", pct(m.attended_to_enrolled_rate), "Lead→Inscrito", pct(m.lead_to_enrolled_rate));
    writeMetricRow(doc, page, "Confianza", pct(m.confidence_score), "Desorden estructural", safeNum(m.structural_disorder_score));
    writeMetricRow(doc, page, "Calidad del dato", pct(m.data_quality_score), "Costo de oportunidad total", money((cost.totalImpact || 0)));
    writeMetricRow(doc, page, "Costo de oportunidad anualizado", money((cost.annualImpact || 0)), "+1% conversión (valor)", money((cost.extraRevenuePerPoint || 0)));
    if (Array.isArray(m.funnel_notes) && m.funnel_notes.length) {
      writeParagraph(doc, page, `Notas de consistencia: ${m.funnel_notes.join(" | ")}`);
    }

    writeSectionTitle(doc, page, "4. Preguntas y respuestas completas");
    questions.forEach((q, i) => {
      ensureSpace(doc, page, 46);
      writeLabel(doc, page, `${i + 1}. ${q.label}`);
      writeParagraph(doc, page, `Respuesta: ${getAnswerLabel(q, state.responses[q.id])}`, 10.5, 0.9);
      page.y += 4;
    });

    writeSectionTitle(doc, page, "5. Cuello principal");
    writeParagraph(doc, page, d.principal ? d.principal.bottleneck : "Sin definir");

    writeSectionTitle(doc, page, "6. Causa raíz");
    writeParagraph(doc, page, d.principal ? d.principal.causeRoot : "Sin definir");

    writeSectionTitle(doc, page, "7. Solución");
    writeParagraph(doc, page, d.principal ? d.principal.solution : "Sin definir");

    writeSectionTitle(doc, page, "8. Productos SuperLeads recomendados");
    if (d.principal && Array.isArray(d.principal.products)) {
      writePdfProductCards(doc, page, d.principal.products);
    } else {
      writeParagraph(doc, page, "Sin recomendación.");
    }

    writeSectionTitle(doc, page, "9. Cuellos secundarios");
    if (Array.isArray(d.secondary) && d.secondary.length) {
      d.secondary.forEach((s) => writeBullet(doc, page, `${s.bottleneck} | Causa raíz: ${s.causeRoot}`));
    } else {
      writeParagraph(doc, page, "Sin cuellos secundarios en este corte.");
    }

    addPage(doc, page, logoAsset);
    writeFinalStatementPage(doc, page, "Este reporte busca claridad comercial, no perfección contable.");

    doc.save(`${filename}.pdf`);
    state.pdfAutoDownloaded = true;
    saveState();

    if (!isAutomatic) {
      alert("Reporte descargado correctamente.");
    }
  } catch (_error) {
    window.print();
    if (!isAutomatic) {
      alert("No se pudo generar el PDF. Se activó la impresión como respaldo.");
    }
  }
}

function prepareDarkPage(doc, page, logoAsset) {
  doc.setFillColor(0, 0, 0);
  doc.rect(0, 0, page.width, page.height, "F");
  drawPdfHeaderLogo(doc, page, logoAsset);
  doc.setDrawColor(48, 48, 48);
  doc.setLineWidth(0.7);
  doc.roundedRect(page.contentX, page.marginTop - 18, page.contentWidth, page.height - page.marginTop - page.marginBottom + 8, 8, 8, "S");
  doc.setDrawColor(90, 90, 90);
  doc.line(page.contentX, page.marginTop - 2, page.contentX + page.contentWidth, page.marginTop - 2);
  doc.setTextColor(255, 255, 255);
  writeFooter(doc, page);
}

function addPage(doc, page, logoAsset = page.logoAsset || null) {
  doc.addPage();
  page.number += 1;
  page.y = page.marginTop + 8;
  prepareDarkPage(doc, page, logoAsset);
}

function ensureSpace(doc, page, requiredHeight) {
  const maxY = page.height - page.marginBottom;
  if (page.y + requiredHeight > maxY) {
    addPage(doc, page, page.logoAsset || null);
  }
}

function writeCover(doc, page, status) {
  page.y = page.marginTop + 28;
  const cx = page.contentX + (page.contentWidth / 2);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(33);
  drawCenteredText(doc, "Rayos X Conversacional", cx, page.y);
  page.y += 36;
  doc.setFontSize(27);
  drawCenteredText(doc, "SuperLeads", cx, page.y);
  page.y += 30;

  doc.setDrawColor(110, 110, 110);
  doc.setLineWidth(1.1);
  doc.line(page.contentX + 36, page.y, page.contentX + page.contentWidth - 36, page.y);
  page.y += 24;

  drawHighlightBox(doc, page, {
    title: "Diagnóstico",
    value: status,
    subtitle: `${state.basicData.institutionName || "Institución sin nombre"} • ${state.basicData.institutionUrl || "URL sin dato"} • Sello CDMX: ${page.reportStamp ? page.reportStamp.full : formatMexicoCitySeal(new Date()).full}`,
    compact: true
  });

  page.y += 18;
  writeParagraph(doc, page, "Radiografía guiada del sistema de inscripciones.", 13, 0.9, true);
  writeParagraph(doc, page, "Tus respuestas nos permiten encontrar el cuello más probable del sistema.", 12, 0.8, true);
}

function writeCostPage(doc, page, cost) {
  page.y = page.marginTop + 22;
  const cx = page.contentX + (page.contentWidth / 2);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(28);
  drawCenteredText(doc, "Costo de no hacer nada", cx, page.y);
  page.y += 20;
  doc.setFontSize(11.5);
  doc.setTextColor(195, 195, 195);
  drawCenteredText(doc, "Estimación comercial de oportunidad perdida (1 sola página de decisión).", cx, page.y);
  doc.setTextColor(255, 255, 255);

  page.y += 26;
  drawHighlightBox(doc, page, {
    title: "Impacto estimado en 12 meses",
    value: money(cost.annualImpact),
    subtitle: "Ingreso potencial no capturado por mantener el sistema actual.",
    compact: false
  });

  page.y += 16;
  writeParagraph(
    doc,
    page,
    `Fórmula base: colegiatura promedio (${money(cost.averageTuition || 0)}) × meses promedio (${safeNum(cost.averageMonths)}) = valor total por alumno (${money(cost.valuePerSeat || 0)}).`,
    10.5,
    0.78,
    true
  );
  writeParagraph(
    doc,
    page,
    `Fórmula de oportunidad: estudiantes en riesgo (${safeNum(cost.lostStudentsEquivalent)}) × valor por alumno (${money(cost.valuePerSeat || 0)}) = costo de oportunidad total (${money(cost.totalImpact)}).`,
    10.5,
    0.78,
    true
  );
  page.y += 4;
  writeMetricRow(doc, page, "Brecha estimada de inscritos", safeNum(cost.enrollmentGap), "Capacidad ociosa estimada", safeNum(cost.idleSeats));
  writeMetricRow(doc, page, "Estudiantes en riesgo (base)", safeNum(cost.lostStudentsEquivalent), "Valor por alumno", money(cost.valuePerSeat || 0));
  writeMetricRow(doc, page, "Costo de oportunidad total", money(cost.totalImpact), "Impacto mensual estimado", money(cost.monthlyImpact));
  writeMetricRow(doc, page, "Impacto anualizado", money(cost.annualImpact), "Escenario 18 meses", money(cost.eighteenMonthImpact));
  writeMetricRow(doc, page, "+1% conversión = alumnos extra", safeNum(cost.extraStudentsPerPoint), "+1% conversión = valor extra", money(cost.extraRevenuePerPoint));
  drawImpactScenarioChart(doc, page, cost);

  page.y += 16;
  writeParagraph(doc, page, `Lectura ejecutiva: ${cost.executiveText}`, 12, 0.9, true);
  if (cost.assumptionsNote) {
    writeParagraph(doc, page, `Supuesto aplicado: ${cost.assumptionsNote}`, 10.6, 0.72, true);
  }
  writeParagraph(doc, page, "Este cálculo es determinístico con la información compartida. Si faltan datos, se usa la estimación más conservadora disponible y se marca como preliminar.", 10.8, 0.75, true);
}

function drawExecutiveSnapshot(doc, page, diagnostic, cost, metrics) {
  const principal = diagnostic.principal || {};
  const cards = [
    {
      title: "Cuello principal",
      value: principal.bottleneck || "Sin definir",
      subtitle: principal.visibleIssue || "Sin síntoma priorizado"
    },
    {
      title: "Causa raíz dominante",
      value: principal.causeRoot || "Sin definir",
      subtitle: `Confianza del hallazgo: ${pct(metrics.confidence_score)}`
    },
    {
      title: "Oportunidad anualizada",
      value: money(cost.annualImpact || 0),
      subtitle: `Costo total estimado: ${money(cost.totalImpact || 0)}`,
      accent: true
    }
  ];

  drawInsightCardGrid(doc, page, cards, 3);
}

function drawInsightCardGrid(doc, page, cards, columns = 3) {
  const gutter = 10;
  const width = (page.contentWidth - (gutter * (columns - 1))) / columns;
  const measured = cards.map((card) => measureInsightCard(doc, width, card));
  const rowHeight = Math.max(...measured.map((item) => item.height), 96);
  ensureSpace(doc, page, rowHeight + 10);

  measured.forEach((card, index) => {
    const x = page.contentX + ((width + gutter) * index);
    drawInsightCard(doc, x, page.y, width, rowHeight, card);
  });

  page.y += rowHeight + 12;
  snapBaseline(page);
}

function measureInsightCard(doc, width, card) {
  const textWidth = width - 22;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  const titleLines = doc.splitTextToSize(String(card.title || ""), textWidth);

  doc.setFont("helvetica", "bold");
  doc.setFontSize(card.accent ? 17 : 14);
  fitTextSize(doc, String(card.value || ""), textWidth, 10.5);
  const valueSize = doc.getFontSize();
  const valueLines = doc.splitTextToSize(String(card.value || ""), textWidth);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9.5);
  const subtitleLines = doc.splitTextToSize(String(card.subtitle || ""), textWidth);

  const height = 18 + (titleLines.length * 12) + (valueLines.length * (valueSize + 2)) + (subtitleLines.length * 11) + 20;
  return { ...card, titleLines, valueLines, subtitleLines, valueSize, height };
}

function drawInsightCard(doc, x, y, width, height, card) {
  if (card.accent) {
    doc.setFillColor(10, 56, 209);
    doc.setDrawColor(47, 102, 255);
  } else {
    doc.setFillColor(11, 11, 11);
    doc.setDrawColor(62, 62, 62);
  }
  doc.roundedRect(x, y, width, height, 10, 10, "FD");

  let cursorY = y + 18;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.setTextColor(card.accent ? 225 : 178, card.accent ? 232 : 178, card.accent ? 255 : 178);
  card.titleLines.forEach((line) => {
    doc.text(String(line), x + 11, cursorY);
    cursorY += 12;
  });

  doc.setFont("helvetica", "bold");
  doc.setFontSize(card.valueSize);
  doc.setTextColor(255, 255, 255);
  cursorY += 4;
  card.valueLines.forEach((line) => {
    doc.text(String(line), x + 11, cursorY);
    cursorY += card.valueSize + 2;
  });

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9.5);
  doc.setTextColor(card.accent ? 232 : 170, card.accent ? 239 : 170, card.accent ? 255 : 170);
  cursorY += 2;
  card.subtitleLines.forEach((line) => {
    doc.text(String(line), x + 11, cursorY);
    cursorY += 11;
  });
  doc.setTextColor(255, 255, 255);
}

function drawPdfFunnelChart(doc, page, metrics) {
  const rows = [
    { label: "Leads", value: metrics.leads },
    { label: "Contactados", value: metrics.contacted },
    { label: "Citas", value: metrics.appointments },
    { label: "Asistieron", value: metrics.attended },
    { label: "Inscritos", value: metrics.enrolled }
  ];
  const maxValue = Math.max(...rows.map((row) => numericOrZero(row.value)), 1);
  const highlight = metrics.break_stage && metrics.break_stage.label ? metrics.break_stage.label : "";
  const boxHeight = 188;
  ensureSpace(doc, page, boxHeight + 10);

  const x = page.contentX;
  const y = page.y;
  const width = page.contentWidth;
  doc.setFillColor(9, 9, 9);
  doc.setDrawColor(58, 58, 58);
  doc.roundedRect(x, y, width, boxHeight, 10, 10, "FD");

  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(184, 184, 184);
  doc.text("Embudo visual del periodo", x + 14, y + 18);

  let rowY = y + 38;
  rows.forEach((row) => {
    const isHighlight = row.label === highlight;
    const barWidth = width - 118;
    const fillWidth = Math.max(0, Math.round((numericOrZero(row.value) / maxValue) * barWidth));

    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(220, 220, 220);
    doc.text(row.label, x + 14, rowY);
    const valueText = safeNum(row.value);
    doc.text(valueText, x + width - 14 - doc.getTextWidth(valueText), rowY);

    doc.setFillColor(26, 26, 26);
    doc.roundedRect(x + 14, rowY + 8, barWidth, 10, 5, 5, "F");
    if (fillWidth > 0) {
      if (isHighlight) {
        doc.setFillColor(16, 74, 255);
      } else {
        doc.setFillColor(232, 232, 232);
      }
      doc.roundedRect(x + 14, rowY + 8, fillWidth, 10, 5, 5, "F");
    }

    if (isHighlight) {
      doc.setTextColor(140, 181, 255);
      doc.setFontSize(8.5);
      doc.text("Ruptura dominante", x + 14, rowY + 24);
    }

    rowY += 28;
  });

  doc.setTextColor(255, 255, 255);
  page.y += boxHeight + 12;
  snapBaseline(page);
}

function drawPdfRateCards(doc, page, metrics) {
  const cards = [
    { title: "Lead → Contactado", value: metrics.lead_to_contact_rate },
    { title: "Contactado → Cita", value: metrics.contacted_to_appointment_rate },
    { title: "Cita → Asistencia", value: metrics.appointment_to_attended_rate },
    { title: "Asistencia → Inscripción", value: metrics.attended_to_enrolled_rate }
  ];
  const columns = 2;
  const gutter = 10;
  const width = (page.contentWidth - gutter) / columns;
  const rowHeight = 78;
  ensureSpace(doc, page, (rowHeight * 2) + gutter + 8);

  cards.forEach((card, index) => {
    const col = index % columns;
    const row = Math.floor(index / columns);
    const x = page.contentX + (col * (width + gutter));
    const y = page.y + (row * (rowHeight + gutter));
    const pctValue = Number.isFinite(card.value) ? Math.round(card.value * 100) : 0;

    doc.setFillColor(11, 11, 11);
    doc.setDrawColor(58, 58, 58);
    doc.roundedRect(x, y, width, rowHeight, 9, 9, "FD");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10);
    doc.setTextColor(185, 185, 185);
    doc.text(card.title, x + 12, y + 18);
    doc.setFontSize(18);
    doc.setTextColor(255, 255, 255);
    doc.text(`${pctValue}%`, x + 12, y + 40);

    doc.setFillColor(26, 26, 26);
    doc.roundedRect(x + 12, y + 50, width - 24, 9, 4, 4, "F");
    doc.setFillColor(pctValue < 35 ? 16 : 232, pctValue < 35 ? 74 : 232, 255);
    doc.roundedRect(x + 12, y + 50, Math.max(0, ((width - 24) * pctValue) / 100), 9, 4, 4, "F");
  });

  doc.setTextColor(255, 255, 255);
  page.y += (rowHeight * 2) + gutter + 12;
  snapBaseline(page);
}

function drawImpactScenarioChart(doc, page, cost) {
  const scenarios = [
    { label: "Mensual", value: cost.monthlyImpact },
    { label: "12 meses", value: cost.annualImpact },
    { label: "18 meses", value: cost.eighteenMonthImpact }
  ];
  const maxValue = Math.max(...scenarios.map((item) => numericOrZero(item.value)), 1);
  const boxHeight = 122;
  ensureSpace(doc, page, boxHeight + 10);

  const x = page.contentX;
  const y = page.y;
  const width = page.contentWidth;
  doc.setFillColor(9, 9, 9);
  doc.setDrawColor(58, 58, 58);
  doc.roundedRect(x, y, width, boxHeight, 10, 10, "FD");

  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(184, 184, 184);
  doc.text("Escenarios de impacto", x + 14, y + 18);

  const barWidth = width - 132;
  let rowY = y + 42;
  scenarios.forEach((item, index) => {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(220, 220, 220);
    doc.text(item.label, x + 14, rowY);
    const valueText = money(item.value || 0);
    doc.text(valueText, x + width - 14 - doc.getTextWidth(valueText), rowY);
    doc.setFillColor(24, 24, 24);
    doc.roundedRect(x + 70, rowY - 8, barWidth, 10, 5, 5, "F");
    const fillWidth = Math.max(4, Math.round((numericOrZero(item.value) / maxValue) * barWidth));
    const fillColor = index === 1 ? [16, 74, 255] : [235, 235, 235];
    doc.setFillColor(fillColor[0], fillColor[1], fillColor[2]);
    doc.roundedRect(x + 70, rowY - 8, fillWidth, 10, 5, 5, "F");
    rowY += 26;
  });

  doc.setTextColor(255, 255, 255);
  page.y += boxHeight + 12;
  snapBaseline(page);
}

function writePdfProductCards(doc, page, products) {
  const list = normalizeRecommendedProducts(products, { forceThree: false });
  if (!list.length) {
    writeParagraph(doc, page, "Sin recomendación.");
    return;
  }

  const gutter = 10;
  const baseWidth = (page.contentWidth - gutter) / 2;
  let cursorY = page.y;

  for (let i = 0; i < list.length; i += 2) {
    const first = getProductMeta(list[i]);
    const second = list[i + 1] ? getProductMeta(list[i + 1]) : null;
    const rowCards = second ? [first, second] : [first];
    const rowWidth = second ? baseWidth : page.contentWidth;
    const measured = rowCards.map((card) => measurePdfProductCard(doc, rowWidth, card));
    const rowHeight = Math.max(...measured.map((card) => card.height), 72);
    ensureSpace(doc, page, rowHeight + 8);
    cursorY = page.y;

    measured.forEach((card, idx) => {
      const x = page.contentX + (idx * (baseWidth + gutter));
      drawPdfProductCard(doc, x, cursorY, second ? baseWidth : page.contentWidth, rowHeight, card);
    });

    cursorY += rowHeight + 10;
    page.y = cursorY;
  }

  snapBaseline(page);
}

function measurePdfProductCard(doc, width, product) {
  const textWidth = width - 24;
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11.5);
  const lines = doc.splitTextToSize(String(product.name || ""), textWidth);
  return {
    ...product,
    lines,
    height: 28 + (lines.length * 14) + 14
  };
}

function drawPdfProductCard(doc, x, y, width, height, product) {
  doc.setFillColor(10, 56, 209);
  doc.setDrawColor(47, 102, 255);
  doc.roundedRect(x, y, width, height, 10, 10, "FD");
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11.5);
  doc.setTextColor(255, 255, 255);
  let cursorY = y + 22;
  product.lines.forEach((line) => {
    doc.text(String(line), x + 12, cursorY);
    cursorY += 14;
  });
  doc.setTextColor(224, 234, 255);
  doc.setFontSize(9);
  doc.text("Producto recomendado de SuperLeads", x + 12, y + height - 12);
  doc.setTextColor(255, 255, 255);
}

function drawHighlightBox(doc, page, payload) {
  const width = page.contentWidth;
  const subtitleLines = doc.splitTextToSize(String(payload.subtitle || ""), width - 38);
  const minHeight = payload.compact ? 108 : 136;
  const baseHeight = payload.compact ? 86 : 108;
  const boxHeight = Math.max(minHeight, baseHeight + (subtitleLines.length * 12));
  ensureSpace(doc, page, boxHeight + 10);
  const x = page.contentX;
  const y = page.y;
  doc.setDrawColor(80, 80, 80);
  doc.setFillColor(12, 12, 12);
  doc.roundedRect(x, y, width, boxHeight, 10, 10, "FD");
  const cx = x + (width / 2);

  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.setTextColor(185, 185, 185);
  drawCenteredText(doc, payload.title, cx, y + 24);

  doc.setFont("helvetica", "bold");
  doc.setFontSize(payload.compact ? 24 : 36);
  fitTextSize(doc, String(payload.value || "N/D"), width - 32, payload.compact ? 17 : 26);
  doc.setTextColor(255, 255, 255);
  const valueY = y + (payload.compact ? 56 : 72);
  drawCenteredText(doc, payload.value, cx, valueY);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(payload.compact ? 10.2 : 11);
  doc.setTextColor(185, 185, 185);
  const baseY = valueY + (payload.compact ? 22 : 26);
  subtitleLines.forEach((line, index) => {
    drawCenteredText(doc, line, cx, baseY + (index * 12));
  });
  doc.setTextColor(255, 255, 255);

  page.y += boxHeight;
}

function writeFinalStatementPage(doc, page, text) {
  const boxWidth = Math.min(page.contentWidth * 0.8, 420);
  const lines = doc.splitTextToSize(String(text || ""), boxWidth - 34);
  const boxHeight = Math.max(92, 54 + (lines.length * 14));
  const x = page.contentX + ((page.contentWidth - boxWidth) / 2);
  const usableHeight = page.height - page.marginTop - page.marginBottom;
  const y = page.marginTop + ((usableHeight - boxHeight) / 2);

  doc.setDrawColor(90, 90, 90);
  doc.setFillColor(12, 12, 12);
  doc.roundedRect(x, y, boxWidth, boxHeight, 12, 12, "FD");

  doc.setFont("helvetica", "bold");
  doc.setFontSize(13);
  doc.setTextColor(255, 255, 255);
  lines.forEach((line, idx) => {
    drawCenteredText(doc, line, x + (boxWidth / 2), y + 36 + (idx * 15));
  });
}

function writeSectionTitle(doc, page, text) {
  ensureSpace(doc, page, 34);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(15);
  doc.setTextColor(255, 255, 255);
  doc.text(text, page.contentX, page.y);
  page.y += 10;
  doc.setDrawColor(70, 70, 70);
  doc.line(page.contentX, page.y, page.contentX + page.contentWidth, page.y);
  page.y += 12;
  snapBaseline(page);
}

function writeLabel(doc, page, text) {
  ensureSpace(doc, page, 16);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.setTextColor(235, 235, 235);
  doc.text(text, page.contentX, page.y);
  page.y += 13;
  snapBaseline(page);
}

function writeParagraph(doc, page, text, fontSize = 11, opacity = 0.88, centered = false) {
  ensureSpace(doc, page, 20);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(fontSize);
  const color = Math.round(255 * Math.max(0.45, Math.min(opacity, 1)));
  doc.setTextColor(color, color, color);
  const lines = doc.splitTextToSize(text, page.contentWidth);
  lines.forEach((line) => {
    ensureSpace(doc, page, 14);
    if (centered) {
      drawCenteredText(doc, line, page.contentX + (page.contentWidth / 2), page.y);
    } else {
      doc.text(line, page.contentX, page.y);
    }
    page.y += 14;
  });
  doc.setTextColor(255, 255, 255);
  snapBaseline(page);
}

function writeBullet(doc, page, text) {
  ensureSpace(doc, page, 18);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(11);
  doc.setTextColor(220, 220, 220);
  const lines = doc.splitTextToSize(`• ${text}`, page.contentWidth);
  lines.forEach((line) => {
    ensureSpace(doc, page, 14);
    doc.text(line, page.contentX, page.y);
    page.y += 14;
  });
  doc.setTextColor(255, 255, 255);
  snapBaseline(page);
}

function writeMetricRow(doc, page, leftLabel, leftValue, rightLabel, rightValue) {
  const left = measureMetricCell(doc, page.columnWidth, leftLabel, leftValue);
  const right = measureMetricCell(doc, page.columnWidth, rightLabel, rightValue);
  const rowHeight = Math.max(left.height, right.height, 46);
  ensureSpace(doc, page, rowHeight + 8);
  const boxWidth = page.columnWidth;
  const y = page.y;
  drawMetricCell(doc, page.contentX, y, boxWidth, rowHeight, left);
  drawMetricCell(doc, page.contentX + boxWidth + page.gutter, y, boxWidth, rowHeight, right);
  page.y += rowHeight + 8;
  snapBaseline(page);
}

function measureMetricCell(doc, width, label, value) {
  const safeLabel = String(label || "Dato");
  const safeValue = String(value || "N/D");
  const textWidth = Math.max(10, width - 20);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9.5);
  fitTextSize(doc, safeLabel, textWidth, 8.2);
  const labelSize = doc.getFontSize();
  const labelLines = doc.splitTextToSize(safeLabel, textWidth);

  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  fitTextSize(doc, safeValue, textWidth, 9);
  const valueSize = doc.getFontSize();
  const valueLines = doc.splitTextToSize(safeValue, textWidth);

  const lineGap = 3;
  const topPad = 10;
  const middlePad = 6;
  const bottomPad = 9;
  const labelBlock = labelLines.length * (labelSize + lineGap);
  const valueBlock = valueLines.length * (valueSize + lineGap - 0.5);
  const height = Math.ceil(topPad + labelBlock + middlePad + valueBlock + bottomPad);

  return {
    label: safeLabel,
    value: safeValue,
    labelLines,
    valueLines,
    labelSize,
    valueSize,
    height
  };
}

function drawMetricCell(doc, x, y, width, height, measured) {
  doc.setFillColor(10, 10, 10);
  doc.setDrawColor(60, 60, 60);
  doc.roundedRect(x, y, width, height, 7, 7, "FD");

  doc.setFont("helvetica", "normal");
  doc.setFontSize(measured.labelSize);
  doc.setTextColor(170, 170, 170);
  let cursorY = y + 10 + measured.labelSize;
  measured.labelLines.forEach((line) => {
    doc.text(String(line), x + 10, cursorY);
    cursorY += measured.labelSize + 3;
  });

  doc.setFont("helvetica", "bold");
  doc.setFontSize(measured.valueSize);
  doc.setTextColor(255, 255, 255);
  cursorY += 2;
  measured.valueLines.forEach((line) => {
    doc.text(String(line), x + 10, cursorY);
    cursorY += measured.valueSize + 2.5;
  });
}

function computeCostOfInaction(metrics) {
  const targetNew = ensureNonNegative(metrics.targetNew);
  const projected = ensureNonNegative(metrics.projected_new_enrolled);
  const enrollmentGap = Math.max(targetNew - projected, 0);
  const idleSeats = ensureNonNegative(metrics.capacity_available);
  const valuePerSeat = ensureNonNegative(metrics.valuePerSeat);
  const averageTuition = ensureNonNegative(metrics.averageTuition);
  const averageMonths = ensureNonNegative(metrics.averageMonths);
  const leads = ensureNonNegative(metrics.leads);

  // Base comercial conservadora: estudiantes en riesgo = max(brecha de meta, capacidad ociosa).
  const lostStudentsEquivalent = Math.max(enrollmentGap, idleSeats);
  // Costo total por ciclo de vida promedio por alumno.
  const totalImpact = lostStudentsEquivalent * valuePerSeat;
  // Conversión a mensual usando meses promedio por alumno; fallback a 1 mes para no diluir el cálculo.
  const cycleMonths = averageMonths > 0 ? averageMonths : 1;
  const monthlyImpact = totalImpact / cycleMonths;
  // Anualización estándar para lectura ejecutiva.
  const annualImpact = monthlyImpact * 12;

  const extraStudentsPerPoint = leads * 0.01;
  const extraRevenuePerPoint = extraStudentsPerPoint * valuePerSeat;
  const assumptions = [];
  if (averageMonths <= 0) {
    assumptions.push("No se reportó meses promedio; se tomó 1 mes base para convertir a mensual y anualizar.");
  }
  if (!valuePerSeat) {
    assumptions.push("No se reportó valor por alumno; los montos de oportunidad se muestran en 0.");
  }

  let executiveText = "Con los datos actuales, la institución está dejando ingreso relevante sobre la mesa.";
  if (!valuePerSeat) {
    executiveText = "No se reportó colegiatura o meses promedio; el cálculo de oportunidad está subestimado y debe refinarse.";
  } else if (lostStudentsEquivalent === 0) {
    executiveText = "En este corte la pérdida estimada es baja, pero puede crecer si cae conversión o aumenta la capacidad ociosa.";
  } else if (annualImpact > 0) {
    executiveText = `Si no corrigen el sistema, el costo anualizado estimado ronda ${money(annualImpact)}.`;
  }

  return {
    enrollmentGap,
    idleSeats,
    lostStudentsEquivalent,
    averageTuition,
    averageMonths,
    valuePerSeat,
    totalImpact,
    annualImpact,
    monthlyImpact,
    sixMonthImpact: monthlyImpact * 6,
    eighteenMonthImpact: monthlyImpact * 18,
    extraStudentsPerPoint,
    extraRevenuePerPoint,
    assumptionsNote: assumptions.join(" "),
    executiveText
  };
}

function money(value) {
  const safe = Number.isFinite(value) ? value : 0;
  return new Intl.NumberFormat("es-MX", {
    style: "currency",
    currency: "MXN",
    maximumFractionDigits: 0
  }).format(safe);
}

function ensureNonNegative(value) {
  return Number.isFinite(value) && value > 0 ? value : 0;
}

function formatMoneyByCurrency(value, currencyCode) {
  const safe = Number.isFinite(value) ? value : 0;
  const map = {
    MXN: { locale: "es-MX", currency: "MXN" },
    USD: { locale: "en-US", currency: "USD" },
    COL: { locale: "es-CO", currency: "COP" }
  };
  const cfg = map[currencyCode] || map.MXN;
  return new Intl.NumberFormat(cfg.locale, {
    style: "currency",
    currency: cfg.currency,
    maximumFractionDigits: 0
  }).format(safe);
}

function convertCurrency(amount, fromCurrency, toCurrency) {
  if (!Number.isFinite(amount)) return 0;
  const fromRate = FX_RATES_TO_MXN[fromCurrency] || 1;
  const toRate = FX_RATES_TO_MXN[toCurrency] || 1;
  const amountInMxn = amount * fromRate;
  return amountInMxn / toRate;
}

function syncLayout(page) {
  page.contentX = page.marginX;
  page.contentWidth = page.width - (page.marginX * 2);
  page.columnWidth = (page.contentWidth - page.gutter) / 2;
  page.y = page.marginTop;
}

function snapBaseline(page) {
  const step = page.baseline || 4;
  page.y = Math.ceil(page.y / step) * step;
}

function drawCenteredText(doc, text, centerX, y) {
  const textWidth = doc.getTextWidth(String(text || ""));
  doc.text(String(text || ""), centerX - (textWidth / 2), y);
}

function drawPdfHeaderLogo(doc, page, logoAsset) {
  if (!logoAsset || !logoAsset.dataUrl || !Number.isFinite(logoAsset.ratio) || logoAsset.ratio <= 0) return;
  const targetWidth = Math.min(176, page.contentWidth * 0.32);
  const targetHeight = targetWidth / logoAsset.ratio;
  const x = (page.width - targetWidth) / 2;
  const y = 14;
  try {
    doc.addImage(logoAsset.dataUrl, "PNG", x, y, targetWidth, targetHeight, undefined, "FAST");
  } catch (_error) {
    // Si el logo falla, no bloqueamos la generación del PDF.
  }
}

function getPdfLogoAsset() {
  if (pdfLogoCache) return Promise.resolve(pdfLogoCache);
  if (pdfLogoPromise) return pdfLogoPromise;

  pdfLogoPromise = new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          resolve(null);
          return;
        }
        ctx.drawImage(img, 0, 0);
        const dataUrl = canvas.toDataURL("image/png");
        const ratio = img.naturalWidth / img.naturalHeight;
        pdfLogoCache = { dataUrl, ratio };
        resolve(pdfLogoCache);
      } catch (_error) {
        resolve(null);
      }
    };
    img.onerror = () => resolve(null);
    img.src = SUPERLEADS_LOGO_URL;
  }).finally(() => {
    pdfLogoPromise = null;
  });

  return pdfLogoPromise;
}

function writeFooter(doc, page) {
  const y = page.height - 30;
  doc.setDrawColor(60, 60, 60);
  doc.setLineWidth(0.6);
  doc.line(page.contentX, y - 12, page.contentX + page.contentWidth, y - 12);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8.8);
  doc.setTextColor(140, 140, 140);
  const sealText = page.reportStamp ? ` · CDMX ${page.reportStamp.short}` : "";
  const left = `SuperLeads · Rayos X Conversacional${sealText}`;
  const right = `Página ${page.number}`;
  doc.text(left, page.contentX, y);
  doc.text(right, page.contentX + page.contentWidth - doc.getTextWidth(right), y);
  doc.setTextColor(255, 255, 255);
}

function fitTextSize(doc, text, maxWidth, minSize) {
  let size = doc.getFontSize();
  while (size > minSize && doc.getTextWidth(text) > maxWidth) {
    size -= 0.4;
    doc.setFontSize(size);
  }
}

function getReportFilename() {
  const institution = (state.basicData.institutionName || "Institucion").trim();
  const safeInstitution = institution
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-zA-Z0-9\s_-]/g, "")
    .trim()
    .replace(/\s+/g, "_") || "Institucion";

  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  const hour = String(now.getHours()).padStart(2, "0");
  const min = String(now.getMinutes()).padStart(2, "0");

  return `Rayos_X_Conversacional_${safeInstitution}_${year}_${month}_${day}_${hour}_${min}`;
}

function formatDateTime(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")} ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

function formatMexicoCitySeal(date) {
  const formatter = new Intl.DateTimeFormat("es-MX", {
    timeZone: "America/Mexico_City",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "numeric",
    minute: "2-digit",
    hour12: true
  });

  const parts = formatter.formatToParts(date).reduce((acc, part) => {
    acc[part.type] = part.value;
    return acc;
  }, {});

  const day = parts.day || "00";
  const month = parts.month || "00";
  const year = parts.year || "0000";
  const hour = parts.hour || "0";
  const minute = parts.minute || "00";
  const period = normalizeDayPeriod(parts.dayPeriod || "");

  return {
    short: `${hour}:${minute} ${period}`,
    full: `${day}/${month}/${year} ${hour}:${minute} ${period}`
  };
}

function normalizeDayPeriod(value) {
  const raw = String(value || "").toLowerCase();
  if (raw.includes("a")) return "a. m.";
  if (raw.includes("p")) return "p. m.";
  return raw || "h";
}

function loadState() {
  const base = {
    startedAt: null,
    finishedAt: null,
    currentStep: 0,
    basicData: {
      institutionUrl: "",
      institutionName: "",
      yearsOperating: "",
      fullName: "",
      phone: "",
      email: ""
    },
    responses: {},
    leadCadence: {
      daily: "",
      monthly: "",
      yearly: ""
    },
    tuitionInput: {
      amount: "",
      currency: "MXN"
    },
    metrics: null,
    diagnosticResult: null,
    pdfAutoDownloaded: false
  };

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return base;
    const parsed = JSON.parse(raw);
    return {
      ...base,
      ...parsed,
      basicData: { ...base.basicData, ...(parsed.basicData || {}) },
      responses: { ...(parsed.responses || {}) },
      leadCadence: { ...base.leadCadence, ...(parsed.leadCadence || {}) },
      tuitionInput: { ...base.tuitionInput, ...(parsed.tuitionInput || {}) }
    };
  } catch (_error) {
    return base;
  }
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function safeNum(value, fallback = "N/D") {
  if (!Number.isFinite(value)) return fallback;
  if (Math.abs(value % 1) < 0.0001) return String(Math.round(value));
  return value.toFixed(2);
}

function numericOrZero(value) {
  return Number.isFinite(value) ? value : 0;
}

function formatBool(value) {
  if (value === null || value === undefined) return "N/D";
  return value ? "Sí" : "No";
}

function isLow(value, threshold) {
  return Number.isFinite(value) && value < threshold;
}

function dedupe(items) {
  return [...new Set(items)];
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
