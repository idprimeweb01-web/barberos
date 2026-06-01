import requests

BASE = "http://127.0.0.1:5000"

def ok(label, r):
    status = "OK" if r.status_code < 400 else "ERRO"
    print(f"\n[{status}] {label} — HTTP {r.status_code}")
    try:
        import json
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    except Exception:
        print(r.text)
    return r

# ── 1. Cadastra barbeiro ───────────────────────────────────────────────────────
r = ok("POST /auth/register (barbeiro)", requests.post(f"{BASE}/auth/register", json={
    "nome": "Lucas Barbeiro", "telefone": "11955550001",
    "email": "lucas@barbearia.com", "senha": "senha123", "perfil": "barbeiro",
    "comissao_percentual": 45.00
}))
barbeiro_usuario_id = r.json().get("usuario", {}).get("id")

# ── 2. Login ───────────────────────────────────────────────────────────────────
r = ok("POST /auth/login", requests.post(f"{BASE}/auth/login", json={
    "email": "lucas@barbearia.com", "senha": "senha123"
}))
token = r.json().get("token")
headers = {"Authorization": f"Bearer {token}"}

# ── 3. Configura agenda do barbeiro ────────────────────────────────────────────
ok("PUT /configuracao-agenda", requests.put(f"{BASE}/configuracao-agenda", headers=headers, json={
    "horario_abertura": "09:00", "horario_fechamento": "18:00",
    "intervalo_minutos": 60, "loja_aberta": True
}))

# ── 4. Lista barbeiros (público) e captura barbeiro_id ────────────────────────
r = ok("GET /barbeiros", requests.get(f"{BASE}/barbeiros"))
barbeiros = r.json()
bid = barbeiros[-1]["id"] if barbeiros else None
print(f"  >> barbeiro_id capturado: {bid}")

# ── 5. Serviços do barbeiro (sem vínculo ainda — lista vazia esperada) ─────────
ok(f"GET /barbeiros/{bid}/servicos", requests.get(f"{BASE}/barbeiros/{bid}/servicos"))

# ── 6. Horários disponíveis (público) ─────────────────────────────────────────
ok("GET /agenda/horarios-disponiveis", requests.get(
    f"{BASE}/agenda/horarios-disponiveis", params={"barbeiro_id": bid, "data": "2026-06-01"}
))

# ── 7. Cliente cria agendamento (sem serviço vinculado — deve falhar) ──────────
ok("POST /agendamentos (sem vínculo barbeiro-servico)", requests.post(f"{BASE}/agendamentos", json={
    "nome": "Carlos Cliente", "telefone": "11977770000",
    "barbeiro_id": bid, "servico_id": 1, "data_hora": "2026-06-01T09:00"
}))

# ── 8. Agendamento manual pelo barbeiro ───────────────────────────────────────
ok("POST /agenda/agendamento-manual", requests.post(
    f"{BASE}/agenda/agendamento-manual", headers=headers, json={
        "nome": "Pedro Teste", "telefone": "11966660000",
        "servico_id": 1, "data": "2026-06-01"
    }
))

# ── 9. Meus agendamentos ──────────────────────────────────────────────────────
ok("GET /agenda/meus-agendamentos", requests.get(
    f"{BASE}/agenda/meus-agendamentos", headers=headers, params={"data": "2026-06-01"}
))

# ── 10. Bloqueia horário ──────────────────────────────────────────────────────
r = ok("POST /horarios-bloqueados", requests.post(f"{BASE}/horarios-bloqueados", headers=headers, json={
    "data_hora_inicio": "2026-06-01T12:00", "data_hora_fim": "2026-06-01T14:00",
    "motivo": "Almoço"
}))
bloqueio_id = r.json().get("bloqueio", {}).get("id")

# ── 11. Horários disponíveis após bloqueio ────────────────────────────────────
ok("GET /agenda/horarios-disponiveis (após bloqueio)", requests.get(
    f"{BASE}/agenda/horarios-disponiveis", params={"barbeiro_id": bid, "data": "2026-06-01"}
))

# ── 12. Desbloqueia ───────────────────────────────────────────────────────────
if bloqueio_id:
    ok(f"DELETE /horarios-bloqueados/{bloqueio_id}", requests.delete(
        f"{BASE}/horarios-bloqueados/{bloqueio_id}", headers=headers
    ))

print("\n\n=== Testes concluídos ===")
