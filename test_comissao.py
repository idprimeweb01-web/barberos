import requests

BASE = "http://127.0.0.1:5000"

def ok(label, r):
    status = "OK" if r.status_code < 400 else "ERRO"
    import json
    print(f"\n[{status}] {label} -- HTTP {r.status_code}")
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    return r

# ── Corrige comissao do Lucas direto no banco ──────────────────────────────────
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from app import create_app, db
from app.models import Barbeiro

app = create_app()
with app.app_context():
    lucas = Barbeiro.query.filter_by(id=1).first()
    if lucas:
        lucas.comissao_percentual = 0
        db.session.commit()
        print(f"[DB] Lucas (barbeiro id=1) -> comissao_percentual = {float(lucas.comissao_percentual)}%")
    else:
        print("[DB] Barbeiro id=1 nao encontrado")

# ── Login como admin (caio@barbearia.com, id=1) ────────────────────────────────
r = ok("POST /auth/login (admin)", requests.post(f"{BASE}/auth/login", json={
    "email": "caio@barbearia.com", "senha": "123456"
}))
token_admin = r.json().get("token")
headers_admin = {"Authorization": f"Bearer {token_admin}"}

# ── Login como barbeiro (lucas) ────────────────────────────────────────────────
r = ok("POST /auth/login (barbeiro)", requests.post(f"{BASE}/auth/login", json={
    "email": "lucas@barbearia.com", "senha": "senha123"
}))
token_barbeiro = r.json().get("token")
headers_barbeiro = {"Authorization": f"Bearer {token_barbeiro}"}

# ── Testa acesso negado (barbeiro tentando alterar comissao) ───────────────────
ok("PUT /auth/admin/barbeiros/1/comissao (barbeiro -- deve falhar 403)",
   requests.put(f"{BASE}/auth/admin/barbeiros/1/comissao",
                headers=headers_barbeiro, json={"comissao_percentual": 50}))

# ── Admin define comissao do Lucas para 40% ────────────────────────────────────
ok("PUT /auth/admin/barbeiros/1/comissao (admin -- deve passar)",
   requests.put(f"{BASE}/auth/admin/barbeiros/1/comissao",
                headers=headers_admin, json={"comissao_percentual": 40}))

# ── Validacao: valor fora do range ─────────────────────────────────────────────
ok("PUT /auth/admin/barbeiros/1/comissao (valor 110 -- deve falhar)",
   requests.put(f"{BASE}/auth/admin/barbeiros/1/comissao",
                headers=headers_admin, json={"comissao_percentual": 110}))

# ── Cadastro de novo barbeiro -- comissao deve ser 0 ──────────────────────────
r = ok("POST /auth/register (novo barbeiro)", requests.post(f"{BASE}/auth/register", json={
    "nome": "Rafa Novo", "telefone": "11944440002",
    "email": "rafa@barbearia.com", "senha": "senha123", "perfil": "barbeiro"
}))
novo_uid = r.json().get("usuario", {}).get("id")

with app.app_context():
    b = Barbeiro.query.filter_by(usuario_id=novo_uid).first()
    if b:
        print(f"\n[DB] Rafa (usuario_id={novo_uid}) -> comissao_percentual = {float(b.comissao_percentual)}%")

print("\n=== Testes concluidos ===")
