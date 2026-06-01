/**
 * Cloudflare Worker — Rayos X SuperLeads
 * Muestra página de mantenimiento cuando el origen devuelve 502/503/504.
 */

const MAINTENANCE_HTML = `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>SuperLeads — Volvemos en un momento</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{background:#040f36;color:#aac4ff;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
         min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px;}
    .card{background:rgba(4,15,54,0.9);border:1px solid rgba(42,137,251,0.2);border-radius:20px;
          padding:52px 44px;max-width:520px;width:100%;text-align:center;}
    .logo{font-size:13px;font-weight:700;color:#56ef9f;letter-spacing:0.12em;text-transform:uppercase;
          margin-bottom:36px;display:flex;align-items:center;justify-content:center;gap:8px;}
    .dot{width:7px;height:7px;border-radius:50%;background:#56ef9f;
         animation:pulse 1.8s ease-in-out infinite;}
    @keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.7)}}
    h1{font-size:1.8rem;font-weight:700;color:#f0f6ff;margin-bottom:14px;line-height:1.2;}
    p{color:rgba(170,196,255,0.6);line-height:1.7;font-size:15px;margin-bottom:10px;}
    .sub{font-size:12px;color:rgba(170,196,255,0.3);margin-top:32px;}
    .btn{display:inline-block;margin-top:28px;padding:12px 32px;background:rgba(42,137,251,0.15);
         border:1px solid rgba(42,137,251,0.35);border-radius:10px;color:#2a89fb;
         text-decoration:none;font-weight:600;font-size:14px;cursor:pointer;}
  </style>
</head>
<body>
  <div class="card">
    <div class="logo"><div class="dot"></div>SuperLeads</div>
    <h1>Volvemos en un momento</h1>
    <p>El sistema de Rayos X está en mantenimiento momentáneo.<br/>Regresa en unos minutos.</p>
    <p>Si tienes tu número de sesión lo podrás recuperar cuando volvamos.</p>
    <a class="btn" href="javascript:location.reload()">↺ Reintentar</a>
    <div class="sub">rayosx.superleads.mx · SuperLeads Sistema de Inscripciones</div>
  </div>
</body>
</html>`;

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  const url = new URL(request.url);

  // Health check público del Worker (para monitoreo externo sin pasar al origen)
  if (url.pathname === '/cf-health') {
    return new Response(JSON.stringify({ status: 'ok', worker: 'rayosx-gateway', ts: Date.now() }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Pasar al origen
  let response;
  try {
    response = await fetch(request);
  } catch (err) {
    return maintenancePage();
  }

  // Si el origen falla, mostrar página amigable
  if (response.status === 502 || response.status === 503 || response.status === 504) {
    return maintenancePage();
  }

  return response;
}

function maintenancePage() {
  return new Response(MAINTENANCE_HTML, {
    status: 503,
    headers: {
      'Content-Type': 'text/html;charset=UTF-8',
      'Retry-After': '60',
      'Cache-Control': 'no-store'
    }
  });
}
