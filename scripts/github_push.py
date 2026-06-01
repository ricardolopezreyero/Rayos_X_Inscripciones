"""
github_push.py — Sube todos los archivos del repo a GitHub via REST API.
Úsalo cuando git push no puede conectar.

Uso: python3 scripts/github_push.py
"""
import os, base64, json, urllib.request, urllib.error, time

TOKEN  = "TU_GITHUB_TOKEN_AQUI"
OWNER  = "ricardolopezreyero"
REPO   = "Rayos_X_Inscripciones"
BRANCH = "main"
BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Archivos a NO subir (igual que .gitignore)
SKIP_PATTERNS = [
    '.db', '.db-shm', '.db-wal', '.pyc', '.pyo',
    '.DS_Store', '.log', '/backups/', '/archivo/',
    'static/pdfs/', '__pycache__', '.git/',
    'cloudflared/credentials.json',
]

def should_skip(path):
    for p in SKIP_PATTERNS:
        if p in path:
            return True
    return False

PROXY = "https://github-proxy.noisy-shape-4fc9.workers.dev"

def api(method, endpoint, data=None):
    url = f"{PROXY}{endpoint}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method, headers={
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "SuperLeads-Push",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return json.loads(body) if body else {}, e.code

def get_file_sha(path):
    """Obtiene el SHA del archivo si ya existe en el repo."""
    resp, status = api("GET", f"/repos/{OWNER}/{REPO}/contents/{path}?ref={BRANCH}")
    if status == 200:
        return resp.get("sha")
    return None

def upload_file(rel_path, full_path):
    with open(full_path, "rb") as f:
        content = base64.b64encode(f.read()).decode()
    sha = get_file_sha(rel_path)
    payload = {
        "message": f"update {rel_path}",
        "content": content,
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha
    resp, status = api("PUT", f"/repos/{OWNER}/{REPO}/contents/{rel_path}", payload)
    return status in (200, 201)

def main():
    # Verificar token y repo
    print("Conectando a GitHub API...")
    resp, status = api("GET", f"/repos/{OWNER}/{REPO}")
    if status != 200:
        print(f"✗ No se pudo acceder al repo: {status} {resp.get('message','')}")
        return

    print(f"✓ Repo encontrado: {resp['full_name']}")
    print()

    # Recolectar archivos
    files = []
    for root, dirs, filenames in os.walk(BASE):
        # Excluir directorios ignorados
        dirs[:] = [d for d in dirs if not should_skip(os.path.join(root, d) + "/")]
        for fname in filenames:
            full = os.path.join(root, fname)
            rel  = os.path.relpath(full, BASE)
            if not should_skip(rel) and not rel.startswith('.git'):
                files.append((rel, full))

    print(f"Subiendo {len(files)} archivos...\n")
    ok = 0
    fail = 0
    for rel, full in sorted(files):
        try:
            success = upload_file(rel, full)
            if success:
                print(f"  ✓ {rel}")
                ok += 1
            else:
                print(f"  ✗ {rel} (falló)")
                fail += 1
        except Exception as e:
            print(f"  ✗ {rel} → {e}")
            fail += 1
        time.sleep(0.3)  # Respetar rate limit de GitHub

    print(f"\n{'='*50}")
    print(f"✓ Subidos: {ok}   ✗ Fallidos: {fail}")
    print(f"Ver resultado: https://github.com/{OWNER}/{REPO}")

if __name__ == "__main__":
    main()
