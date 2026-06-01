import requests, json, sys, os

BASE = "http://127.0.0.1:5000"

def show(label, r):
    status = "OK" if r.status_code < 400 else "ERRO"
    print(f"\n[{status}] {label} -- HTTP {r.status_code}")
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    return r

# ── Tokens ─────────────────────────────────────────────────────────────────────
token_admin = requests.post(f"{BASE}/auth/login", json={"email": "caio@barbearia.com", "senha": "123456"}).json()["token"]
token_barb  = requests.post(f"{BASE}/auth/login", json={"email": "lucas@barbearia.com", "senha": "senha123"}).json()["token"]
adm  = {"Authorization": f"Bearer {token_admin}"}
barb = {"Authorization": f"Bearer {token_barb}"}
print("Tokens obtidos.")

# ── Setup: garante estoque na pomada (id=1) ────────────────────────────────────
# Consulta admin para saber o estoque atual
prod_list = requests.get(f"{BASE}/admin/produtos", headers=adm).json()
pomada = next((p for p in prod_list if p["id"] == 1), None)
estoque_atual = pomada["quantidade_estoque"] if pomada else 0
if estoque_atual < 5:
    show(f"PUT /produtos/1/estoque (+{20 - estoque_atual} -- reabastece)", requests.put(
        f"{BASE}/produtos/1/estoque", headers=adm, json={"quantidade": 20 - estoque_atual}
    ))
else:
    print(f"\n[INFO] Pomada ja tem {estoque_atual} unidades em estoque.")

# ── Setup: cria agendamento para o teste ─────────────────────────────────────
r = show("POST /agendamentos (cria para o teste)", requests.post(f"{BASE}/agendamentos", json={
    "nome": "Ana Teste", "telefone": "11922220001",
    "barbeiro_id": 1, "servico_id": 1, "data_hora": "2026-07-01T10:00"
}))
ag_id = r.json().get("agendamento", {}).get("id")
print(f"\n[INFO] agendamento_id = {ag_id}")

# ═══════════════════════════════════════════════════════════════════════════════
print("\n\n====== FLUXO DE CAIXA ======")

# 1. Abre atendimento
r = show("POST /atendimentos (abre)", requests.post(f"{BASE}/atendimentos",
    headers=barb, json={"agendamento_id": ag_id}))
at_id = r.json().get("atendimento", {}).get("id")
print(f"\n[INFO] atendimento_id = {at_id}")

# 2. Tenta abrir de novo (deve falhar 409)
show("POST /atendimentos (duplicado -- 409)", requests.post(f"{BASE}/atendimentos",
    headers=barb, json={"agendamento_id": ag_id}))

# 3. Visualiza atendimento (1 item: servico)
show(f"GET /atendimentos/{at_id}", requests.get(f"{BASE}/atendimentos/{at_id}", headers=barb))

# 4. Adiciona produto (Pomada 2 unidades)
r = show(f"POST /atendimentos/{at_id}/itens (pomada x2)", requests.post(
    f"{BASE}/atendimentos/{at_id}/itens", headers=barb,
    json={"tipo": "produto", "produto_id": 1, "quantidade": 2}
))
item_id = r.json().get("item", {}).get("id")

# 5. Adiciona servico extra
show(f"POST /atendimentos/{at_id}/itens (servico extra)", requests.post(
    f"{BASE}/atendimentos/{at_id}/itens", headers=barb,
    json={"tipo": "servico", "servico_id": 1, "quantidade": 1}
))

# 6. Remove o servico extra (terceiro item)
itens = requests.get(f"{BASE}/atendimentos/{at_id}", headers=barb).json().get("itens", [])
if len(itens) >= 3:
    item_extra_id = itens[2]["id"]
    show(f"DELETE /atendimentos/{at_id}/itens/{item_extra_id} (remove extra)", requests.delete(
        f"{BASE}/atendimentos/{at_id}/itens/{item_extra_id}", headers=barb
    ))

# 7. Visualiza atendimento final antes de efetuar (servico + pomada x2)
show(f"GET /atendimentos/{at_id} (antes de efetuar)", requests.get(
    f"{BASE}/atendimentos/{at_id}", headers=barb))

# 8. Tenta efetuar com forma invalida
show("PUT /efetuar (forma invalida -- 400)", requests.put(
    f"{BASE}/atendimentos/{at_id}/efetuar", headers=barb,
    json={"forma_pagamento": "boleto"}
))

# 9. Efetua o atendimento com pix
show(f"PUT /atendimentos/{at_id}/efetuar (pix)", requests.put(
    f"{BASE}/atendimentos/{at_id}/efetuar", headers=barb,
    json={"forma_pagamento": "pix"}
))

# 10. Tenta efetuar de novo (deve falhar)
show("PUT /efetuar (ja efetuado -- 400)", requests.put(
    f"{BASE}/atendimentos/{at_id}/efetuar", headers=barb,
    json={"forma_pagamento": "pix"}
))

# 11. Confirma estoque da pomada foi abatido
prod_apos = requests.get(f"{BASE}/admin/produtos", headers=adm).json()
pomada_apos = next((p for p in prod_apos if p["id"] == 1), None)
print(f"\n[ESTOQUE] Pomada apos atendimento: {pomada_apos['quantidade_estoque']} unidades | ativo={pomada_apos['ativo']}")

# 12. Confirma agendamento virou 'concluido'
sys.path.insert(0, os.path.dirname(__file__))
from app import create_app, db
from app.models import Agendamento
with create_app().app_context():
    ag = db.session.get(Agendamento, ag_id)
    print(f"[DB] Agendamento {ag_id} status = '{ag.status}'")

# 13. Lista atendimentos do dia
show("GET /atendimentos?data=2026-07-01 (barbeiro)", requests.get(
    f"{BASE}/atendimentos", headers=barb, params={"data": "2026-07-01"}
))

# 14. Tenta adicionar item em atendimento ja efetuado
show(f"POST /atendimentos/{at_id}/itens (ja efetuado -- 400)", requests.post(
    f"{BASE}/atendimentos/{at_id}/itens", headers=barb,
    json={"tipo": "produto", "produto_id": 1, "quantidade": 1}
))

print("\n\n=== Testes concluidos ===")
