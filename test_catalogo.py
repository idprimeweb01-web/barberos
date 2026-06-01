import requests, json

BASE = "http://127.0.0.1:5000"

def show(label, r):
    status = "OK" if r.status_code < 400 else "ERRO"
    print(f"\n[{status}] {label} -- HTTP {r.status_code}")
    print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    return r

# ── Tokens ─────────────────────────────────────────────────────────────────────
token_admin    = requests.post(f"{BASE}/auth/login", json={"email": "caio@barbearia.com", "senha": "123456"}).json()["token"]
token_barbeiro = requests.post(f"{BASE}/auth/login", json={"email": "lucas@barbearia.com", "senha": "senha123"}).json()["token"]
adm  = {"Authorization": f"Bearer {token_admin}"}
barb = {"Authorization": f"Bearer {token_barbeiro}"}
print("Tokens obtidos.")

# ═══════════════════════════════════════════════════════════════════════════════
print("\n\n====== SERVICOS ======")

# Barbeiro nao pode criar servico
show("POST /servicos (barbeiro -- 403)", requests.post(f"{BASE}/servicos", headers=barb,
    json={"nome": "Corte", "duracao_minutos": 30, "preco": 35}))

# Admin cria dois servicos
r = show("POST /servicos -- Corte Simples", requests.post(f"{BASE}/servicos", headers=adm,
    json={"nome": "Corte Simples", "descricao": "Corte na tesoura", "duracao_minutos": 30, "preco": 35.00}))
sid1 = r.json().get("servico", {}).get("id")

r = show("POST /servicos -- Corte + Barba", requests.post(f"{BASE}/servicos", headers=adm,
    json={"nome": "Corte + Barba", "duracao_minutos": 60, "preco": 55.00}))
sid2 = r.json().get("servico", {}).get("id")

# Lista publico
show("GET /servicos (publico)", requests.get(f"{BASE}/servicos"))

# Edita servico
show(f"PUT /servicos/{sid1}", requests.put(f"{BASE}/servicos/{sid1}", headers=adm,
    json={"preco": 40.00, "descricao": "Corte na tesoura ou maquina"}))

# Vincula servico 1 ao barbeiro 1 (Lucas)
show(f"POST /servicos/{sid1}/barbeiros/1 (vincula)", requests.post(
    f"{BASE}/servicos/{sid1}/barbeiros/1", headers=adm))

# Tenta vincular de novo (409)
show(f"POST /servicos/{sid1}/barbeiros/1 (duplicado -- 409)", requests.post(
    f"{BASE}/servicos/{sid1}/barbeiros/1", headers=adm))

# Vincula servico 2
show(f"POST /servicos/{sid2}/barbeiros/1", requests.post(
    f"{BASE}/servicos/{sid2}/barbeiros/1", headers=adm))

# Confirma via rota de agenda
show("GET /barbeiros/1/servicos (agenda)", requests.get(f"{BASE}/barbeiros/1/servicos"))

# Desvincula servico 2
show(f"DELETE /servicos/{sid2}/barbeiros/1", requests.delete(
    f"{BASE}/servicos/{sid2}/barbeiros/1", headers=adm))

# Soft delete servico 2
show(f"DELETE /servicos/{sid2} (soft delete)", requests.delete(
    f"{BASE}/servicos/{sid2}", headers=adm))

# Lista publico apos soft delete
show("GET /servicos (apos soft delete)", requests.get(f"{BASE}/servicos"))

# ═══════════════════════════════════════════════════════════════════════════════
print("\n\n====== PRODUTOS ======")

# Admin cria produto com estoque
r = show("POST /produtos -- Pomada (estoque 10)", requests.post(f"{BASE}/produtos", headers=adm,
    json={"nome": "Pomada Modeladora", "categoria": "Finalizacao", "preco": 29.90, "quantidade_estoque": 10}))
pid1 = r.json().get("produto", {}).get("id")

# Produto sem estoque (nasce inativo)
r = show("POST /produtos -- Oleo (sem estoque)", requests.post(f"{BASE}/produtos", headers=adm,
    json={"nome": "Oleo de Barba", "categoria": "Barba", "preco": 45.00, "quantidade_estoque": 0}))
pid2 = r.json().get("produto", {}).get("id")

# Lista publica (so ativos com estoque > 0)
show("GET /produtos (publico)", requests.get(f"{BASE}/produtos"))

# Lista admin (todos)
show("GET /admin/produtos (admin)", requests.get(f"{BASE}/admin/produtos", headers=adm))

# Edita produto
show(f"PUT /produtos/{pid1}", requests.put(f"{BASE}/produtos/{pid1}", headers=adm,
    json={"preco": 32.90, "categoria": "Cabelo"}))

# Ajusta estoque: adiciona 5
show(f"PUT /produtos/{pid1}/estoque (+5)", requests.put(
    f"{BASE}/produtos/{pid1}/estoque", headers=adm, json={"quantidade": 5}))

# Abastece produto inativo (pid2 = 0) -> reativa
show(f"PUT /produtos/{pid2}/estoque (+3 -- reativa produto)", requests.put(
    f"{BASE}/produtos/{pid2}/estoque", headers=adm, json={"quantidade": 3}))

# Zera estoque do pid1 -> desativa automaticamente
show(f"PUT /produtos/{pid1}/estoque (-15 -- zera e desativa)", requests.put(
    f"{BASE}/produtos/{pid1}/estoque", headers=adm, json={"quantidade": -15}))

# Tenta remover mais do que tem (erro)
show(f"PUT /produtos/{pid2}/estoque (-99 -- estoque insuficiente)", requests.put(
    f"{BASE}/produtos/{pid2}/estoque", headers=adm, json={"quantidade": -99}))

# Soft delete pid2
show(f"DELETE /produtos/{pid2} (soft delete)", requests.delete(
    f"{BASE}/produtos/{pid2}", headers=adm))

# Lista admin final
show("GET /admin/produtos (estado final)", requests.get(f"{BASE}/admin/produtos", headers=adm))

print("\n\n=== Testes concluidos ===")
