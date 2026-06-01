#!/usr/bin/env python
"""
test_perfis.py -- Valida o sistema de perfis super_admin / gestor / barbeiro.
"""
import json
import sys
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app import create_app

app = create_app()
cli = app.test_client()

# ── Helpers ────────────────────────────────────────────────────────────────────

def _h(token=None):
    h = {'Content-Type': 'application/json'}
    if token:
        h['Authorization'] = f'Bearer {token}'
    return h

def post(url, data=None, token=None):
    r = cli.post(url, data=json.dumps(data or {}), headers=_h(token))
    return r.status_code, (r.get_json() or {})

def get(url, token=None, **params):
    qs = '&'.join(f'{k}={v}' for k, v in params.items())
    full = f'{url}?{qs}' if qs else url
    r = cli.get(full, headers=_h(token))
    return r.status_code, (r.get_json() or {})

def put(url, data=None, token=None):
    r = cli.put(url, data=json.dumps(data or {}), headers=_h(token))
    return r.status_code, (r.get_json() or {})

# ── Resultados ─────────────────────────────────────────────────────────────────

_falhas = []
_n = 0

def ok(descricao, passou, detalhe=''):
    global _n
    _n += 1
    label = ' OK   ' if passou else 'FALHOU'
    print(f"  [{label}] {_n:02d}. {descricao}")
    if detalhe:
        print(f"           -> {detalhe}")
    if not passou:
        _falhas.append(_n)
    return passou

# ══════════════════════════════════════════════════════════════════════════════
print(f'\n{"="*60}')
print('  TESTE DE PERFIS -- BarberOS')
print(f'{"="*60}\n')

# ── 1. Login super_admin ───────────────────────────────────────────────────────
print('=== 1. Login super_admin ===')
s, r = post('/auth/login', {'email': 'caio@barbearia.com', 'senha': 'senha123'})
SA = r.get('token')
perfil_sa = r.get('usuario', {}).get('perfil')
ok('Login super_admin retorna 200 com token', s == 200 and bool(SA),
   f'perfil={perfil_sa}')
ok('Perfil do token e super_admin', perfil_sa == 'super_admin',
   f'perfil recebido: {perfil_sa}')

# ── 2. Login gestor ────────────────────────────────────────────────────────────
print('\n=== 2. Login gestor ===')
s, r = post('/auth/login', {'email': 'gestor@caio.com', 'senha': 'caio@2026'})
GT = r.get('token')
perfil_gt = r.get('usuario', {}).get('perfil')
barb_id_gt = r.get('usuario', {}).get('barbearia_id')
ok('Login gestor retorna 200 com token', s == 200 and bool(GT),
   f'perfil={perfil_gt} barbearia_id={barb_id_gt}')
ok('Perfil do token e gestor', perfil_gt == 'gestor',
   f'perfil recebido: {perfil_gt}')
ok('Gestor tem barbearia_id no token', barb_id_gt is not None,
   f'barbearia_id={barb_id_gt}')

# ── 3. Super_admin acessa GET /super/barbearias ────────────────────────────────
print('\n=== 3. Super_admin acessa /super/barbearias ===')
s, r = get('/super/barbearias', token=SA)
ok('Super_admin GET /super/barbearias retorna 200', s == 200,
   f'total barbearias={len(r) if isinstance(r, list) else "?"} | resp={str(r)[:80]}')
if isinstance(r, list) and r:
    b0 = r[0]
    ok('Retorna campos tema na barbearia', 'tema' in b0,
       f'campos: {list(b0.get("tema", {}).keys())}')

# ── 4. Gestor NAO acessa /super/barbearias ─────────────────────────────────────
print('\n=== 4. Gestor NAO acessa /super/barbearias ===')
s, r = get('/super/barbearias', token=GT)
ok('Gestor GET /super/barbearias retorna 403', s == 403,
   f'resposta: {r.get("erro")}')

# ── 5. Gestor acessa relatorios da propria barbearia ──────────────────────────
print('\n=== 5. Gestor acessa relatorios ===')
from datetime import date, timedelta
I30 = (date.today() - timedelta(days=30)).isoformat()
FIM = date.today().isoformat()
s, r = get('/relatorios/resumo', token=GT, inicio=I30, fim=FIM)
ok('Gestor GET /relatorios/resumo retorna 200', s == 200,
   f'total_atendimentos={r.get("total_atendimentos")}')

# ── 6. POST /auth/esqueci-senha cria solicitacao ──────────────────────────────
print('\n=== 6. Esqueci-senha cria solicitacao ===')
s, r = post('/auth/esqueci-senha', {'email': 'gestor@caio.com'})
ok('POST /auth/esqueci-senha retorna 200 (generico)', s == 200,
   f'mensagem: {r.get("mensagem")}')

# Email inexistente tambem retorna 200 (nao revela)
s2, r2 = post('/auth/esqueci-senha', {'email': 'nao_existe@test.com'})
ok('Email inexistente tambem retorna 200 (sem revelar)', s2 == 200,
   f'mensagem: {r2.get("mensagem")}')

# ── 7. Gestor lista solicitacoes ───────────────────────────────────────────────
print('\n=== 7. Gestor lista solicitacoes ===')
s, lista = get('/auth/gestor/solicitacoes-senha', token=GT)
ok('Gestor GET /auth/gestor/solicitacoes-senha retorna 200', s == 200,
   f'total pendentes={len(lista) if isinstance(lista, list) else "?"}')

sol_id = None
if isinstance(lista, list) and lista:
    sol = lista[0]
    sol_id = sol.get('id')
    ok('Solicitacao tem email e telefone do usuario', bool(sol.get('email')) and bool(sol.get('telefone')),
       f'email={sol.get("email")} tel={sol.get("telefone")} nome={sol.get("nome")}')
else:
    ok('Solicitacao encontrada', False, 'lista vazia ou erro')

# ── 8. Gestor resolve solicitacao e redefine senha ────────────────────────────
print('\n=== 8. Resolver solicitacao ===')
NOVA_SENHA = 'novaSenha@123'
if sol_id:
    s, r = put(f'/auth/gestor/solicitacoes-senha/{sol_id}/resolver',
               {'nova_senha': NOVA_SENHA}, token=GT)
    ok('PUT /auth/gestor/solicitacoes-senha/<id>/resolver retorna 200', s == 200,
       f'usuario={r.get("usuario", {}).get("nome")} tel={r.get("usuario", {}).get("telefone")}')
else:
    ok('Resolver solicitacao', False, 'sol_id nao disponivel')

# ── 9. Login com nova senha funciona ──────────────────────────────────────────
print('\n=== 9. Login com nova senha ===')
s, r = post('/auth/login', {'email': 'gestor@caio.com', 'senha': NOVA_SENHA})
ok('Login com nova senha retorna 200', s == 200 and bool(r.get('token')),
   f'perfil={r.get("usuario", {}).get("perfil")}')

# Restaura senha original
post('/auth/login', {'email': 'caio@barbearia.com', 'senha': 'senha123'})
s_rest, _ = post('/auth/login', {'email': 'gestor@caio.com', 'senha': 'caio@2026'})
# Cria nova solicitacao e restaura para simplificar
new_sol_s, _ = post('/auth/esqueci-senha', {'email': 'gestor@caio.com'})
s_lst, lst2 = get('/auth/gestor/solicitacoes-senha', token=SA)
if isinstance(lst2, list) and lst2:
    sol2_id = lst2[0].get('id')
    put(f'/auth/gestor/solicitacoes-senha/{sol2_id}/resolver',
        {'nova_senha': 'caio@2026'}, token=SA)

# ── 10. Super_admin cria nova barbearia ───────────────────────────────────────
print('\n=== 10. Super_admin cria nova barbearia ===')
import time
TS = str(int(time.time()))[-6:]
s, r = post('/super/barbearias', {'nome': f'Barbearia Teste {TS}', 'slug': f'teste{TS}'}, token=SA)
ok('Super_admin POST /super/barbearias retorna 201', s == 201,
   f'id={r.get("barbearia", {}).get("id")} slug={r.get("barbearia", {}).get("slug")}')

# ── Resultado final ────────────────────────────────────────────────────────────
print(f'\n{"="*60}')
total  = _n
passou = total - len(_falhas)
print(f'  RESULTADO: {passou}/{total} OK  |  {len(_falhas)} falha(s)')
if _falhas:
    print(f'  Falhas: {_falhas}')
    print(f'{"="*60}\n')
    sys.exit(1)
else:
    print('  Todos os testes de perfil passaram.')
    print(f'{"="*60}\n')
    sys.exit(0)
