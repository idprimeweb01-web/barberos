#!/usr/bin/env python
"""
test_integracao.py -- Teste de integracao ponta a ponta + isolamento multi-tenant.
Usa Flask test client (sem servidor externo necessario).
"""
import json
import sys
import time
from datetime import date, timedelta

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


# ── Resultado ──────────────────────────────────────────────────────────────────

_falhas = []
_ids    = {}
_n      = 0

def ok(descricao, passou, detalhe='', lista_debug=None):
    global _n
    _n += 1
    label = ' OK   ' if passou else 'FALHOU'
    print(f"  [{label}] {_n:02d}. {descricao}")
    if detalhe:
        print(f"           -> {detalhe}")
    if not passou and lista_debug is not None:
        print(f"           -> DEBUG: {lista_debug}")
    if not passou:
        _falhas.append(_n)
    return passou


# ── Dados do teste ─────────────────────────────────────────────────────────────

TS   = str(int(time.time()))[-6:]
SLUG1 = f'b1{TS}'       # slug barbearia 1
SLUG2 = f'b2{TS}'       # slug barbearia 2
DATA  = (date.today() + timedelta(days=1)).isoformat()
I30   = (date.today() - timedelta(days=30)).isoformat()
FIM   = (date.today() + timedelta(days=1)).isoformat()


# ==============================================================================
print(f'\n{"="*64}')
print( '  TESTE DE INTEGRACAO -- BarberOS Multi-Tenant')
print(f'  Sufixo : {TS}  |  Agendamento : {DATA}')
print(f'{"="*64}\n')
# ==============================================================================


# ══════════════════════════════════════════════════════════════════════════════
print('=== BARBEARIA 1 — fluxo completo ===\n')
# ══════════════════════════════════════════════════════════════════════════════

# 1. Criar barbearia 1
print('>> Etapa 1 -- Criar barbearia 1')
s, r = post('/auth/barbearias', {'nome': f'Barbearia Um {TS}', 'slug': SLUG1})
_ids['barb1_id'] = r.get('barbearia', {}).get('id')
ok('Barbearia 1 criada', s == 201, f'id={_ids["barb1_id"]} slug={SLUG1}')

# 2. Admin 1 registra e faz login
print('\n>> Etapa 2 -- Admin e login (barbearia 1)')
s, r = post('/auth/register', {
    'nome': f'Admin1 {TS}', 'telefone': f'11900{TS}',
    'email': f'admin1_{TS}@test.com', 'senha': 'senha123', 'perfil': 'admin',
    'barbearia_slug': SLUG1,
})
ok('Admin 1 registrado', s == 201)

s, r = post('/auth/login', {'email': f'admin1_{TS}@test.com', 'senha': 'senha123'})
A1 = r.get('token')
ok('Admin 1 fez login (JWT com barbearia_id)', s == 200 and bool(A1),
   f'barbearia_id={r.get("usuario", {}).get("barbearia_id")}')

# 3. Criar 2 servicos na barbearia 1
print('\n>> Etapa 3 -- Servicos (barbearia 1)')
s, r = post('/servicos', {'nome': f'Corte {TS}', 'duracao_minutos': 30, 'preco': 40.0}, token=A1)
_ids['s1'] = r.get('servico', {}).get('id')
ok('Servico "Corte" criado', s == 201, f'id={_ids["s1"]}')

s, r = post('/servicos', {'nome': f'Barba {TS}', 'duracao_minutos': 20, 'preco': 25.0}, token=A1)
_ids['s2'] = r.get('servico', {}).get('id')
ok('Servico "Barba" criado', s == 201, f'id={_ids["s2"]}')

# 4. Criar 2 produtos
print('\n>> Etapa 4 -- Produtos (barbearia 1)')
s, r = post('/produtos', {'nome': f'Pomada {TS}', 'preco': 32.0, 'quantidade_estoque': 10}, token=A1)
_ids['p_pomada'] = r.get('produto', {}).get('id')
ok('Produto "Pomada" criado (estoque=10)', s == 201, f'id={_ids["p_pomada"]}')

s, r = post('/produtos', {'nome': f'Oleo {TS}', 'preco': 28.0, 'quantidade_estoque': 5}, token=A1)
_ids['p_oleo'] = r.get('produto', {}).get('id')
ok('Produto "Oleo" criado (estoque=5)', s == 201, f'id={_ids["p_oleo"]}')

# 5. Cadastrar barbeiro
print('\n>> Etapa 5 -- Barbeiro (barbearia 1)')
s, r = post('/auth/register', {
    'nome': f'Joao {TS}', 'telefone': f'11911{TS}',
    'email': f'joao_{TS}@test.com', 'senha': 'senha123', 'perfil': 'barbeiro',
    'barbearia_slug': SLUG1,
})
ok('Barbeiro registrado', s == 201)

s, lista = get(f'/b/{SLUG1}/barbeiros')
barb_obj = next((b for b in (lista if isinstance(lista, list) else [])
                 if b.get('nome') == f'Joao {TS}'), None)
_ids['bid1'] = barb_obj.get('id') if barb_obj else None
ok('Barbeiro aparece em GET /b/<slug>/barbeiros', barb_obj is not None, f'barbeiro_id={_ids["bid1"]}')

# 6. Comissao e vinculos
print('\n>> Etapa 6 -- Comissao e vinculos')
s, r = put(f'/auth/admin/barbeiros/{_ids["bid1"]}/comissao', {'comissao_percentual': 40.0}, token=A1)
ok('Comissao definida em 40%', s == 200 and r.get('barbeiro', {}).get('comissao_percentual') == 40.0)

s, _ = post(f'/servicos/{_ids["s1"]}/barbeiros/{_ids["bid1"]}', token=A1)
ok('Servico "Corte" vinculado', s == 201)
s, _ = post(f'/servicos/{_ids["s2"]}/barbeiros/{_ids["bid1"]}', token=A1)
ok('Servico "Barba" vinculado', s == 201)

# 7. Login barbeiro
print('\n>> Etapa 7 -- Login barbeiro')
s, r = post('/auth/login', {'email': f'joao_{TS}@test.com', 'senha': 'senha123'})
BT1 = r.get('token')
ok('Barbeiro fez login', s == 200 and bool(BT1))

# 8. Configurar agenda
print('\n>> Etapa 8 -- Agenda')
s, r = put('/configuracao-agenda', {
    'horario_abertura': '08:00', 'horario_fechamento': '18:00',
    'intervalo_minutos': 60, 'loja_aberta': True,
}, token=BT1)
ok('Agenda configurada (08:00-18:00, 60min)', s == 200)

# 9. Horarios disponíveis via rota publica
print('\n>> Etapa 9 -- Horarios disponíveis (rota publica /b/<slug>/...)')
s, r = get(f'/b/{SLUG1}/agenda/horarios-disponiveis', barbeiro_id=_ids['bid1'], data=DATA)
slots = r.get('horarios', [])
ok(f'Horarios disponíveis via /b/{SLUG1}/agenda/horarios-disponiveis',
   s == 200 and len(slots) > 0, f'{len(slots)} slots: {slots[:3]}')
slot0     = slots[0] if slots else '08:00'
DATA_HORA = f'{DATA}T{slot0}'

# 10. Agendamento pelo cliente (rota publica com slug)
print('\n>> Etapa 10 -- Agendamento + reserva (rota publica)')
s, r = post(f'/b/{SLUG1}/agendamentos', {
    'nome': 'Carlos Cliente', 'telefone': '11987654321',
    'barbeiro_id': _ids['bid1'], 'servico_id': _ids['s1'],
    'data_hora': DATA_HORA,
    'produtos_reservados': [_ids['p_pomada']],
})
ag = r.get('agendamento', {})
_ids['ag1'] = ag.get('id')
ok(f'Agendamento criado via /b/{SLUG1}/agendamentos', s == 201,
   f'id={_ids["ag1"]} cliente={ag.get("cliente")}')
ok('Reserva de pomada incluída', len(ag.get('produtos_reservados', [])) == 1)

# 11. Cliente criado automaticamente
print('\n>> Etapa 11 -- Cliente automatico')
s, lista_cli = get('/clientes', token=BT1)
cli_obj = next((c for c in (lista_cli if isinstance(lista_cli, list) else [])
                if c.get('nome') == 'Carlos Cliente'), None)
_ids['cli1'] = cli_obj.get('id') if cli_obj else None
ok('Cliente criado automaticamente na barbearia 1', cli_obj is not None,
   f'id={_ids["cli1"]} tel={cli_obj.get("telefone") if cli_obj else "N/A"}')

# 12. Verificar reserva
print('\n>> Etapa 12 -- Reserva')
s, reservas = get(f'/agendamentos/{_ids["ag1"]}/reservas', token=BT1)
reservas = reservas if isinstance(reservas, list) else []
ok('Reserva criada com status "reservado"',
   len(reservas) > 0 and reservas[0].get('status') == 'reservado',
   f'status={reservas[0].get("status") if reservas else "N/A"}')

# 13. Atendimento
print('\n>> Etapa 13 -- Atendimento')
s, r = post('/atendimentos', {'agendamento_id': _ids['ag1']}, token=BT1)
_ids['at1'] = r.get('atendimento', {}).get('id')
ok('Atendimento aberto', s == 201, f'id={_ids["at1"]}')

# 14. Item extra
s, r = post(f'/atendimentos/{_ids["at1"]}/itens', {
    'tipo': 'produto', 'produto_id': _ids['p_oleo'], 'quantidade': 1,
}, token=BT1)
ok('Oleo adicionado como item extra', s == 201,
   f'item={r.get("item", {}).get("nome")}')

# 15. Efetuar pagamento
print('\n>> Etapa 15 -- Efetuar pagamento')
s, r = put(f'/atendimentos/{_ids["at1"]}/efetuar', {'forma_pagamento': 'pix'}, token=BT1)
ok('Atendimento efetuado via PIX', s == 200,
   f'total=R${r.get("atendimento", {}).get("total")}')

# 16. Verificar estoques via API
print('\n>> Etapa 16 -- Estoques')
s, lista_prod = get('/admin/produtos', token=A1)
lista_prod = lista_prod if isinstance(lista_prod, list) else []
pomada_api = next((p for p in lista_prod if p.get('id') == _ids['p_pomada']), None)
oleo_api   = next((p for p in lista_prod if p.get('id') == _ids['p_oleo']),   None)
ok('Estoque da pomada abatido (10 -> 9)', pomada_api and pomada_api.get('quantidade_estoque') == 9,
   f'estoque={pomada_api.get("quantidade_estoque") if pomada_api else "N/A"}')
ok('Estoque do oleo abatido (5 -> 4)',    oleo_api   and oleo_api.get('quantidade_estoque') == 4,
   f'estoque={oleo_api.get("quantidade_estoque") if oleo_api else "N/A"}')

# 17. Reserva confirmada
s, res_pos = get(f'/agendamentos/{_ids["ag1"]}/reservas', token=BT1)
res_pos = res_pos if isinstance(res_pos, list) else []
ok('Reserva da pomada mudou para "confirmado"',
   res_pos and res_pos[0].get('status') == 'confirmado',
   f'status={res_pos[0].get("status") if res_pos else "N/A"}')

# 18. Agendamento concluido
s, lista_ag = get('/agenda/meus-agendamentos', token=BT1, data=DATA)
ag_enc = next((a for a in (lista_ag if isinstance(lista_ag, list) else [])
               if a.get('id') == _ids['ag1']), None)
ok('Agendamento com status "concluido"',
   ag_enc is not None and ag_enc.get('status') == 'concluido',
   f'status={ag_enc.get("status") if ag_enc else "nao encontrado"}')

# 19-21. Relatorios
print('\n>> Etapa 19-21 -- Relatorios (barbearia 1)')
s, r = get('/relatorios/resumo', token=A1, inicio=I30, fim=FIM)
ok('GET /relatorios/resumo retorna 200', s == 200,
   f'atendimentos={r.get("total_atendimentos")} receita=R${r.get("receita_total")}')

s, lista_b = get('/relatorios/por-barbeiro', token=A1, inicio=I30, fim=FIM)
lista_b = lista_b if isinstance(lista_b, list) else []
barb_rel = next((b for b in lista_b if b.get('barbeiro_id') == _ids['bid1']), None)
ok('Barbeiro aparece no relatorio com comissao', barb_rel is not None,
   f'{barb_rel}' if barb_rel else f'bid={_ids["bid1"]} nao encontrado. Lista={lista_b}')

s, lista_pv = get('/relatorios/produtos-mais-vendidos', token=A1, inicio=I30, fim=FIM)
lista_pv = lista_pv if isinstance(lista_pv, list) else []
oleo_rel = next((p for p in lista_pv if p.get('produto_id') == _ids['p_oleo']), None)
ok('Oleo aparece no ranking de vendas', oleo_rel is not None, f'{oleo_rel}')

# 22. Perfil do cliente
print('\n>> Etapa 22 -- Perfil do cliente')
if _ids.get('cli1'):
    s, r = get(f'/clientes/{_ids["cli1"]}/perfil', token=BT1)
    dados = r.get('dados_pessoais', {})
    ok('GET /clientes/<id>/perfil retorna 200', s == 200,
       f'nome={dados.get("nome")} tel={dados.get("telefone")} '
       f'visitas={r.get("total_visitas")} gasto=R${r.get("total_gasto")}')
else:
    ok('Perfil do cliente', False, 'cli1 nao disponivel')


# ══════════════════════════════════════════════════════════════════════════════
print(f'\n{"="*64}')
print('=== BARBEARIA 2 — isolamento multi-tenant ===\n')
# ══════════════════════════════════════════════════════════════════════════════

# 23. Criar barbearia 2
print('>> Etapa 23 -- Criar barbearia 2')
s, r = post('/auth/barbearias', {'nome': f'Barbearia Dois {TS}', 'slug': SLUG2})
_ids['barb2_id'] = r.get('barbearia', {}).get('id')
ok('Barbearia 2 criada', s == 201, f'id={_ids["barb2_id"]} slug={SLUG2}')

# 24. Admin 2 registra e faz login
print('\n>> Etapa 24 -- Admin 2 (barbearia 2)')
s, r = post('/auth/register', {
    'nome': f'Admin2 {TS}', 'telefone': f'11922{TS}',
    'email': f'admin2_{TS}@test.com', 'senha': 'senha123', 'perfil': 'admin',
    'barbearia_slug': SLUG2,
})
ok('Admin 2 registrado na barbearia 2', s == 201,
   f'barbearia_id={r.get("usuario", {}).get("barbearia_id")}')

s, r = post('/auth/login', {'email': f'admin2_{TS}@test.com', 'senha': 'senha123'})
A2 = r.get('token')
ok('Admin 2 fez login', s == 200 and bool(A2))

# 25. Admin 2 cria servico proprio
print('\n>> Etapa 25 -- Servico exclusivo da barbearia 2')
s, r = post('/servicos', {'nome': f'Progressiva {TS}', 'duracao_minutos': 90, 'preco': 120.0}, token=A2)
_ids['s_b2'] = r.get('servico', {}).get('id')
ok('Servico "Progressiva" criado na barbearia 2', s == 201, f'id={_ids["s_b2"]}')

# 26. Admin 1 NAO ve servico da barbearia 2
print('\n>> Etapa 26 -- Isolamento: barbearia 1 nao ve dados da 2')
s, lista_s1 = get('/servicos', token=A1)
lista_s1 = lista_s1 if isinstance(lista_s1, list) else []
ids_s1 = {s.get('id') for s in lista_s1}
ok('Admin 1 NAO ve servico da barbearia 2 em GET /servicos',
   _ids['s_b2'] not in ids_s1,
   f'ids_vistos={ids_s1} | id_b2={_ids["s_b2"]}')

# 27. Admin 2 NAO ve servicos da barbearia 1
s, lista_s2 = get('/servicos', token=A2)
lista_s2 = lista_s2 if isinstance(lista_s2, list) else []
ids_s2 = {s.get('id') for s in lista_s2}
ok('Admin 2 NAO ve servicos da barbearia 1 em GET /servicos',
   _ids['s1'] not in ids_s2 and _ids['s2'] not in ids_s2,
   f'ids_vistos={ids_s2} | ids_b1={_ids["s1"]},{_ids["s2"]}')

# 28. Barbeiros publicos isolados por slug
print('\n>> Etapa 28 -- Isolamento: rotas publicas por slug')
s, lista_barb1 = get(f'/b/{SLUG1}/barbeiros')
lista_barb1 = lista_barb1 if isinstance(lista_barb1, list) else []
s, lista_barb2 = get(f'/b/{SLUG2}/barbeiros')
lista_barb2 = lista_barb2 if isinstance(lista_barb2, list) else []
ids_barb1 = {b.get('id') for b in lista_barb1}
ids_barb2 = {b.get('id') for b in lista_barb2}
ok(f'GET /b/{SLUG1}/barbeiros retorna apenas barbeiros da barbearia 1',
   _ids['bid1'] in ids_barb1 and not ids_barb1.intersection(ids_barb2),
   f'b1={ids_barb1} | b2={ids_barb2}')

# 29. Cliente da barbearia 1 invisível para admin 2
print('\n>> Etapa 29 -- Isolamento: clientes por barbearia')
s, lista_cli2 = get('/clientes', token=A2)
lista_cli2 = lista_cli2 if isinstance(lista_cli2, list) else []
ids_cli2 = {c.get('id') for c in lista_cli2}
ok('Admin 2 NAO ve clientes da barbearia 1',
   _ids['cli1'] not in ids_cli2,
   f'ids_vistos={ids_cli2} | cli_b1={_ids["cli1"]}')

# 30. Relatorio da barbearia 2 zerado (sem atendimentos proprios)
print('\n>> Etapa 30 -- Relatorio barbearia 2 (deve estar zerado)')
s, r = get('/relatorios/resumo', token=A2, inicio=I30, fim=FIM)
ok('Relatorio da barbearia 2 nao inclui dados da barbearia 1',
   s == 200 and r.get('total_atendimentos', 0) == 0,
   f'total_atendimentos={r.get("total_atendimentos")} (esperado: 0)')

# 31. Slug inexistente retorna 404
print('\n>> Etapa 31 -- Slug invalido retorna 404')
s, r = get(f'/b/slug_inexistente_{TS}/barbeiros')
ok('GET /b/<slug_invalido>/barbeiros retorna 404', s == 404, f'erro={r.get("erro")}')


# ==============================================================================
print(f'\n{"="*64}')
total  = _n
passou = total - len(_falhas)
print(f'  RESULTADO: {passou}/{total} passos OK  |  {len(_falhas)} falha(s)')
if _falhas:
    print(f'  Passos com falha: {_falhas}')
    print(f'{"="*64}\n')
    sys.exit(1)
else:
    print('  Todos os passos passaram. Backend multi-tenant validado.')
    print(f'{"="*64}\n')
    sys.exit(0)
