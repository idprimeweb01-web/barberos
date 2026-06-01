#!/usr/bin/env python
"""
test_e2e.py -- Teste End-to-End completo do BarberOS.

Fluxo completo de 17 passos + verificação das rotas corrigidas:
  1.  Super admin cria barbearia "Teste XYZ"
  1b. Super admin lista barbearias via GET /super/barbearias/lista (rota corrigida)
  2.  Super admin cria gestor "Carlos Gestor"
  2b. Super admin lista gestores via GET /super/gestores/lista (rota corrigida)
  3.  Gestor faz login
  4.  Gestor cadastra barbeiro "Pedro Barbeiro"
  5.  Gestor cadastra serviço "Corte Premium" (R$80)
  6.  Gestor cadastra produto "Pomada Premium" (R$35)
  7.  Gestor configura agenda (08:00-18:00, 1h)
  8.  Cliente acessa landing page pública
  9.  Cliente realiza agendamento completo
  10. Cliente vê confirmação do agendamento
  11. Barbeiro faz login
  12. Barbeiro visualiza agendamento na agenda
  13. Barbeiro inicia atendimento (abre caixa)
  14. Barbeiro adiciona produto extra
  15. Barbeiro confirma pagamento PIX
  16. Super admin verifica métricas globais atualizadas
  17. Gestor verifica relatório da barbearia

Requer: servidor Flask rodando em http://127.0.0.1:5000
"""

import sys
import time
from datetime import date, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

try:
    import requests
except ImportError:
    print("ERRO: 'requests' não instalado. Execute: pip install requests")
    sys.exit(1)

# ── Configuração ───────────────────────────────────────────────────────────────
BASE = 'http://127.0.0.1:5000'
TS   = str(int(time.time()))[-6:]

SLUG           = f'testexyz{TS}'
BARB_NOME      = 'Teste XYZ'
GESTOR_NOME    = 'Carlos Gestor'
GESTOR_EMAIL   = f'carlos{TS}@teste.com'
GESTOR_SENHA   = 'senha123'
BARBEIRO_NOME  = 'Pedro Barbeiro'
BARBEIRO_EMAIL = f'pedro{TS}@teste.com'
BARBEIRO_SENHA = 'senha123'
SERVICO_NOME   = 'Corte Premium'
SERVICO_PRECO  = 80.0
PRODUTO_NOME   = 'Pomada Premium'
PRODUTO_PRECO  = 35.0
TOTAL_ESPERADO = SERVICO_PRECO + PRODUTO_PRECO   # 115.0
CLIENTE_NOME   = 'Joao Cliente'
CLIENTE_TEL    = '11987654321'

AMANHA     = (date.today() + timedelta(days=1)).isoformat()
INICIO_REL = (date.today() - timedelta(days=1)).isoformat()
FIM_REL    = (date.today() + timedelta(days=2)).isoformat()

# ── Estado entre passos ────────────────────────────────────────────────────────
S = {}   # state dict
_resultados = []
_falhas     = []
_n          = 0


# ── Helpers ────────────────────────────────────────────────────────────────────

def h(token=None):
    hdrs = {'Content-Type': 'application/json'}
    if token:
        hdrs['Authorization'] = f'Bearer {token}'
    return hdrs


def ok(descricao, passou, detalhe='', debug=None):
    global _n
    _n += 1
    _resultados.append((_n, descricao, passou, detalhe))
    sym = ' OK   ' if passou else 'FALHOU'
    print(f"  [{sym}] {_n:02d}. {descricao}")
    if detalhe:
        print(f"           -> {detalhe}")
    if not passou:
        _falhas.append(_n)
        if debug is not None:
            print(f"           -> DEBUG: {debug}")
    return passou


def req(method, rota, token=None, **kwargs):
    """Faz request e trata erros de conexão."""
    try:
        fn = getattr(requests, method)
        return fn(f'{BASE}{rota}', headers=h(token), timeout=10, **kwargs)
    except requests.exceptions.ConnectionError:
        print(f"\n  ERRO: Sem conexão com {BASE}. Servidor está rodando?\n")
        sys.exit(1)


# ── Cabeçalho ──────────────────────────────────────────────────────────────────
print(f'\n{"="*64}')
print('  TESTE END-TO-END — BarberOS')
print(f'  Sufixo único : {TS}')
print(f'  Slug         : {SLUG}')
print(f'  Data amanhã  : {AMANHA}')
print(f'  Receita total: R${TOTAL_ESPERADO:.2f} (corte R${SERVICO_PRECO} + pomada R${PRODUTO_PRECO})')
print(f'{"="*64}\n')

# ── Verifica servidor ──────────────────────────────────────────────────────────
try:
    r = requests.get(f'{BASE}/login', timeout=5)
    print(f"  Servidor OK (HTTP {r.status_code})\n")
except requests.exceptions.ConnectionError:
    print("  ERRO: Servidor não responde em http://127.0.0.1:5000")
    print("  Inicie com: python run.py\n")
    sys.exit(1)


# ── SETUP: Login super admin ───────────────────────────────────────────────────
print('── Setup: Login Super Admin ──────────────────────────────────')
r = req('post', '/auth/login', json={'email': 'adm@barbearia.com', 'senha': 'senha123'})
S['sa_token'] = r.json().get('token')
ok('Login super admin (adm@barbearia.com)',
   r.status_code == 200 and bool(S['sa_token']),
   f"perfil={r.json().get('usuario', {}).get('perfil')}")


# ══════════════════════════════════════════════════════════════════════════════
print('\n── Passo 1: Criar Barbearia ─────────────────────────────────')
# ══════════════════════════════════════════════════════════════════════════════
r = req('post', '/super/barbearias', token=S['sa_token'],
        json={'nome': BARB_NOME, 'slug': SLUG})
b = r.json().get('barbearia', {})
S['barbearia_id'] = b.get('id')
ok(f'Super admin cria barbearia "{BARB_NOME}" (slug: {SLUG})',
   r.status_code == 201 and bool(S['barbearia_id']),
   f"id={S['barbearia_id']}",
   debug=r.json())


# ── Passo 1b: Listar barbearias pela rota corrigida ──────────────────────────
r = req('get', '/super/barbearias/lista', token=S['sa_token'])
lista_barb = r.json() if r.ok else []
barb_criada = next((b for b in lista_barb if b.get('id') == S['barbearia_id']), None)
ok('GET /super/barbearias/lista retorna barbearia recém-criada (rota corrigida)',
   r.status_code == 200 and barb_criada is not None,
   f"total={len(lista_barb)} barbearia_encontrada={barb_criada.get('nome') if barb_criada else 'NAO ENCONTRADA'} "
   f"tema={barb_criada.get('tema') if barb_criada else '?'}",
   debug=r.json() if not r.ok else None)


# ══════════════════════════════════════════════════════════════════════════════
print('\n── Passo 2: Criar Gestor ────────────────────────────────────')
# ══════════════════════════════════════════════════════════════════════════════
r = req('post', '/super/gestor', token=S['sa_token'],
        json={
            'nome':         GESTOR_NOME,
            'email':        GESTOR_EMAIL,
            'telefone':     '11900000001',
            'senha':        GESTOR_SENHA,
            'barbearia_id': S['barbearia_id'],
        })
u = r.json().get('usuario', {})
S['gestor_id'] = u.get('id')
ok(f'Super admin cria gestor "{GESTOR_NOME}" ({GESTOR_EMAIL})',
   r.status_code == 201 and bool(S['gestor_id']),
   f"id={S['gestor_id']} barbearia_id={u.get('barbearia_id')}",
   debug=r.json())


# ── Passo 2b: Listar gestores pela rota corrigida ────────────────────────────
r = req('get', '/super/gestores/lista', token=S['sa_token'])
lista_gest = r.json() if r.ok else []
gest_criado = next((g for g in lista_gest if g.get('id') == S['gestor_id']), None)
ok('GET /super/gestores/lista retorna gestor recém-criado (rota corrigida)',
   r.status_code == 200 and gest_criado is not None,
   f"total={len(lista_gest)} gestor_encontrado={gest_criado.get('nome') if gest_criado else 'NAO ENCONTRADO'} "
   f"barbearia={gest_criado.get('barbearia') if gest_criado else '?'}",
   debug=r.json() if not r.ok else None)


# ══════════════════════════════════════════════════════════════════════════════
print('\n── Passo 3: Login Gestor ────────────────────────────────────')
# ══════════════════════════════════════════════════════════════════════════════
r = req('post', '/auth/login', json={'email': GESTOR_EMAIL, 'senha': GESTOR_SENHA})
S['gt'] = r.json().get('token')
u = r.json().get('usuario', {})
ok(f'Gestor faz login ({GESTOR_EMAIL})',
   r.status_code == 200 and bool(S['gt']),
   f"perfil={u.get('perfil')} barbearia_id={u.get('barbearia_id')}",
   debug=r.json())


# ══════════════════════════════════════════════════════════════════════════════
print('\n── Passo 4: Cadastrar Barbeiro ──────────────────────────────')
# ══════════════════════════════════════════════════════════════════════════════
r = req('post', '/admin/barbeiros', token=S['gt'],
        json={
            'nome':                BARBEIRO_NOME,
            'email':               BARBEIRO_EMAIL,
            'telefone':            '11900000002',
            'senha':               BARBEIRO_SENHA,
            'comissao_percentual': 40.0,
            'servicos_ids':        [],
        })
barb = r.json().get('barbeiro', {})
S['barbeiro_id']    = barb.get('id')
S['barbeiro_email'] = barb.get('email')
ok(f'Gestor cadastra barbeiro "{BARBEIRO_NOME}" (comissão 40%)',
   r.status_code == 201 and bool(S['barbeiro_id']),
   f"barbeiro_id={S['barbeiro_id']} email={S['barbeiro_email']}",
   debug=r.json())


# ══════════════════════════════════════════════════════════════════════════════
print('\n── Passo 5: Cadastrar Serviço ───────────────────────────────')
# ══════════════════════════════════════════════════════════════════════════════
r = req('post', '/servicos', token=S['gt'],
        json={
            'nome':            SERVICO_NOME,
            'duracao_minutos': 30,
            'preco':           SERVICO_PRECO,
            'descricao':       'Corte premium completo',
        })
sv = r.json().get('servico', {})
S['servico_id'] = sv.get('id')
ok(f'Gestor cadastra serviço "{SERVICO_NOME}" (R${SERVICO_PRECO:.2f}, 30min)',
   r.status_code == 201 and bool(S['servico_id']),
   f"servico_id={S['servico_id']}",
   debug=r.json())

# Vincula serviço ao barbeiro (necessário para agendamento público)
r = req('put', f'/admin/barbeiros/{S["barbeiro_id"]}', token=S['gt'],
        json={'servicos_ids': [S['servico_id']]})
ok(f'Serviço "{SERVICO_NOME}" vinculado ao barbeiro (necessário para booking)',
   r.status_code == 200,
   f"servicos_ids=[{S['servico_id']}]",
   debug=r.json())


# ══════════════════════════════════════════════════════════════════════════════
print('\n── Passo 6: Cadastrar Produto ───────────────────────────────')
# ══════════════════════════════════════════════════════════════════════════════
r = req('post', '/produtos', token=S['gt'],
        json={
            'nome':               PRODUTO_NOME,
            'preco':              PRODUTO_PRECO,
            'quantidade_estoque': 10,
            'categoria':          'Pomadas',
        })
prod = r.json().get('produto', {})
S['produto_id'] = prod.get('id')
ok(f'Gestor cadastra produto "{PRODUTO_NOME}" (R${PRODUTO_PRECO:.2f}, estoque=10)',
   r.status_code == 201 and bool(S['produto_id']),
   f"produto_id={S['produto_id']} estoque={prod.get('quantidade_estoque')}",
   debug=r.json())


# ══════════════════════════════════════════════════════════════════════════════
print('\n── Passo 7: Configurar Agenda ───────────────────────────────')
# ══════════════════════════════════════════════════════════════════════════════
r = req('put', f'/admin/agenda/{S["barbeiro_id"]}', token=S['gt'],
        json={
            'horario_abertura':   '08:00',
            'horario_fechamento': '18:00',
            'intervalo_minutos':  60,
            'loja_aberta':        True,
        })
cfg = r.json().get('configuracao', {})
ok('Gestor configura agenda: 08:00-18:00, intervalo 1h, loja aberta',
   r.status_code == 200 and cfg.get('intervalo_minutos') == 60,
   f"abertura={cfg.get('horario_abertura')} fechamento={cfg.get('horario_fechamento')} intervalo={cfg.get('intervalo_minutos')}min",
   debug=r.json())


# ══════════════════════════════════════════════════════════════════════════════
print('\n── Passo 8: Cliente acessa landing page ─────────────────────')
# ══════════════════════════════════════════════════════════════════════════════
r = req('get', f'/b/{SLUG}/')
ok(f'GET /b/{SLUG}/ retorna 200 (landing page HTML)',
   r.status_code == 200 and 'BarberOS' in r.text,
   f"bytes={len(r.content)}")

r = req('get', f'/b/{SLUG}/barbearia-info')
info = r.json() if r.ok else {}
ok('GET /b/<slug>/barbearia-info retorna tema e nome correto',
   r.status_code == 200 and info.get('nome') == BARB_NOME,
   f"nome={info.get('nome')} cor_primaria={info.get('cor_primaria')}",
   debug=r.json() if not r.ok else None)

r = req('get', f'/b/{SLUG}/barbeiros')
barbeiros_pub = r.json() if r.ok else []
ok(f'GET /b/{SLUG}/barbeiros lista barbeiros públicos',
   r.status_code == 200 and any(b.get('nome') == BARBEIRO_NOME for b in barbeiros_pub),
   f"total={len(barbeiros_pub)} nomes={[b['nome'] for b in barbeiros_pub]}")

r = req('get', f'/b/{SLUG}/servicos')
servicos_pub = r.json() if r.ok else []
ok(f'GET /b/{SLUG}/servicos lista serviços públicos',
   r.status_code == 200 and any(s.get('nome') == SERVICO_NOME for s in servicos_pub),
   f"total={len(servicos_pub)} nomes={[s['nome'] for s in servicos_pub]}")


# ══════════════════════════════════════════════════════════════════════════════
print('\n── Passo 9: Agendamento pelo Cliente ───────────────────────')
# ══════════════════════════════════════════════════════════════════════════════

# Encontra Pedro na lista pública
pedro = next((b for b in barbeiros_pub if b.get('nome') == BARBEIRO_NOME), None)
bid_pub = pedro.get('id') if pedro else None
ok(f'Barbeiro "{BARBEIRO_NOME}" encontrado na lista pública',
   pedro is not None,
   f"barbeiro_id_publico={bid_pub}")

# Serviços do Pedro
r = req('get', f'/b/{SLUG}/barbeiros/{bid_pub}/servicos')
svs_pedro = r.json() if r.ok else []
sv_pub = next((s for s in svs_pedro if s.get('nome') == SERVICO_NOME), None)
ok(f'Serviço "{SERVICO_NOME}" disponível para {BARBEIRO_NOME}',
   r.status_code == 200 and sv_pub is not None,
   f"preco=R${sv_pub.get('preco', '?')} duracao={sv_pub.get('duracao_minutos', '?')}min")

# Horários disponíveis para amanhã
r = req('get', f'/b/{SLUG}/agenda/horarios-disponiveis',
        params={'barbeiro_id': bid_pub, 'data': AMANHA})
slots = r.json().get('horarios', []) if r.ok else []
slot = slots[0] if slots else None
ok(f'Horários disponíveis para {AMANHA} (barbeiro_id={bid_pub})',
   r.status_code == 200 and bool(slots),
   f"total_slots={len(slots)} slots={slots[:4]}...")

# Criar agendamento (fluxo do cliente)
DATA_HORA = f'{AMANHA}T{slot}'
r = req('post', f'/b/{SLUG}/agendamentos',
        json={
            'nome':        CLIENTE_NOME,
            'telefone':    CLIENTE_TEL,
            'barbeiro_id': bid_pub,
            'servico_id':  sv_pub.get('id') if sv_pub else S['servico_id'],
            'data_hora':   DATA_HORA,
        })
ag = r.json().get('agendamento', {})
S['agendamento_id'] = ag.get('id')
ok(f'POST /b/{SLUG}/agendamentos — "{CLIENTE_NOME}" agenda {SERVICO_NOME} às {slot}',
   r.status_code == 201 and bool(S['agendamento_id']),
   f"agendamento_id={S['agendamento_id']} cliente={ag.get('cliente')} servico={ag.get('servico')}",
   debug=r.json() if not r.ok else None)


# ══════════════════════════════════════════════════════════════════════════════
print('\n── Passo 10: Confirmação do Agendamento ─────────────────────')
# ══════════════════════════════════════════════════════════════════════════════
r = req('get', f'/b/{SLUG}/confirmacao/{S["agendamento_id"]}')
ok('Página de confirmação /b/<slug>/confirmacao/<id> retorna 200',
   r.status_code == 200,
   f"status={r.status_code} bytes={len(r.content)}")

r = req('get', f'/b/{SLUG}/agendamento/{S["agendamento_id"]}')
conf = r.json() if r.ok else {}
ok('Dados públicos do agendamento corretos (cliente, barbeiro, serviço)',
   r.status_code == 200
   and conf.get('barbeiro', {}).get('nome') == BARBEIRO_NOME
   and conf.get('servico', {}).get('nome') == SERVICO_NOME,
   f"barbeiro={conf.get('barbeiro',{}).get('nome')} "
   f"servico={conf.get('servico',{}).get('nome')} "
   f"status={conf.get('status')}",
   debug=r.json() if not r.ok else None)


# ══════════════════════════════════════════════════════════════════════════════
print('\n── Passo 11: Login Barbeiro ─────────────────────────────────')
# ══════════════════════════════════════════════════════════════════════════════
r = req('post', '/auth/login', json={'email': BARBEIRO_EMAIL, 'senha': BARBEIRO_SENHA})
S['bt'] = r.json().get('token')
u = r.json().get('usuario', {})
ok(f'Barbeiro faz login ({BARBEIRO_EMAIL})',
   r.status_code == 200 and bool(S['bt']),
   f"perfil={u.get('perfil')} barbearia_id={u.get('barbearia_id')}",
   debug=r.json() if not r.ok else None)


# ══════════════════════════════════════════════════════════════════════════════
print('\n── Passo 12: Agenda do Barbeiro ─────────────────────────────')
# ══════════════════════════════════════════════════════════════════════════════
r = req('get', '/agenda/meus-agendamentos', token=S['bt'], params={'data': AMANHA})
ags = r.json() if r.ok else []
ag_enc = next((a for a in ags if a.get('id') == S['agendamento_id']), None)
ok(f'GET /agenda/meus-agendamentos?data={AMANHA} — encontra agendamento do cliente',
   r.status_code == 200 and ag_enc is not None,
   f"total_agendamentos={len(ags)} "
   f"agendamento_id={S['agendamento_id']} "
   f"cliente={ag_enc.get('cliente') if ag_enc else 'NAO ENCONTRADO'} "
   f"servico={ag_enc.get('servico') if ag_enc else '?'}",
   debug={'ids_encontrados': [a.get('id') for a in ags]} if not ag_enc else None)


# ══════════════════════════════════════════════════════════════════════════════
print('\n── Passo 13: Iniciar Atendimento (Caixa) ────────────────────')
# ══════════════════════════════════════════════════════════════════════════════
r = req('post', f'/agendamentos/{S["agendamento_id"]}/iniciar', token=S['bt'], json={})
at = r.json().get('atendimento', {})
S['atendimento_id'] = at.get('id')
ok('POST /agendamentos/<id>/iniciar — atendimento aberto com item de serviço',
   r.status_code in (200, 201) and bool(S['atendimento_id']),
   f"atendimento_id={S['atendimento_id']} "
   f"status={at.get('status_operacao')} "
   f"itens={len(at.get('itens', []))}",
   debug=r.json() if not r.ok else None)

# Verifica dados completos pelo endpoint de caixa
r = req('get', f'/caixa/agendamento/{S["agendamento_id"]}', token=S['bt'])
cx = r.json()
ok('GET /caixa/agendamento/<id> retorna cliente + serviço + atendimento',
   r.status_code == 200 and cx.get('atendimento') is not None,
   f"cliente={cx.get('cliente', {}).get('nome')} "
   f"servico={cx.get('servico', {}).get('nome')} "
   f"itens={len(cx.get('atendimento', {}).get('itens', []))}",
   debug=r.json() if not r.ok else None)


# ══════════════════════════════════════════════════════════════════════════════
print('\n── Passo 14: Adicionar Produto Extra ────────────────────────')
# ══════════════════════════════════════════════════════════════════════════════
r = req('post', f'/atendimentos/{S["atendimento_id"]}/itens', token=S['bt'],
        json={
            'tipo':       'produto',
            'produto_id': S['produto_id'],
            'quantidade': 1,
        })
item = r.json().get('item', {})
ok(f'POST /atendimentos/<id>/itens — adiciona "{PRODUTO_NOME}" ao atendimento',
   r.status_code == 201 and item.get('nome') == PRODUTO_NOME,
   f"nome={item.get('nome')} "
   f"preco=R${item.get('preco_unitario')} "
   f"subtotal=R${item.get('subtotal')}",
   debug=r.json() if not r.ok else None)

# Verifica total correto após adicionar produto
r = req('get', f'/caixa/agendamento/{S["agendamento_id"]}', token=S['bt'])
cx2 = r.json()
itens_atuais = cx2.get('atendimento', {}).get('itens', [])
total_calc = sum(float(i.get('subtotal', 0)) for i in itens_atuais)
ok(f'Total do atendimento = R${TOTAL_ESPERADO:.2f} (corte + pomada)',
   abs(total_calc - TOTAL_ESPERADO) < 0.01,
   f"total_calculado=R${total_calc:.2f} esperado=R${TOTAL_ESPERADO:.2f} "
   f"itens=[{', '.join(i.get('nome','?') for i in itens_atuais)}]")


# ══════════════════════════════════════════════════════════════════════════════
print('\n── Passo 15: Confirmar Pagamento PIX ───────────────────────')
# ══════════════════════════════════════════════════════════════════════════════
r = req('put', f'/atendimentos/{S["atendimento_id"]}/efetuar', token=S['bt'],
        json={'forma_pagamento': 'pix'})
at_final = r.json().get('atendimento', {})
pag      = r.json().get('pagamento', {})
ok('PUT /atendimentos/<id>/efetuar — pagamento PIX confirmado',
   r.status_code == 200 and at_final.get('status_operacao') == 'efetuado',
   f"status={at_final.get('status_operacao')} "
   f"total=R${at_final.get('total')} "
   f"forma={pag.get('forma_pagamento')} "
   f"pagamento_status={pag.get('status')}",
   debug=r.json() if not r.ok else None)

ok(f'Total cobrado = R${TOTAL_ESPERADO:.2f} (correto)',
   abs(float(at_final.get('total', 0)) - TOTAL_ESPERADO) < 0.01,
   f"total={at_final.get('total')} esperado={TOTAL_ESPERADO}")

# Verifica estoque abatido
r = req('get', '/admin/produtos', token=S['gt'])
prods_pos = r.json() if r.ok else []
pomada_pos = next((p for p in prods_pos if p.get('id') == S['produto_id']), None)
ok(f'Estoque de "{PRODUTO_NOME}" abatido (10 → 9)',
   pomada_pos and pomada_pos.get('quantidade_estoque') == 9,
   f"estoque_atual={pomada_pos.get('quantidade_estoque') if pomada_pos else 'N/A'} "
   f"(esperado: 9)")


# ══════════════════════════════════════════════════════════════════════════════
print('\n── Passo 16: Super Admin — Métricas Globais ─────────────────')
# ══════════════════════════════════════════════════════════════════════════════
r = req('get', '/super/dashboard/metricas', token=S['sa_token'])
met = r.json() if r.ok else {}
ok('GET /super/dashboard/metricas retorna métricas de todas as barbearias',
   r.status_code == 200,
   f"barbearias={met.get('total_barbearias')} "
   f"usuarios={met.get('total_usuarios')} "
   f"faturamento_global=R${met.get('total_faturamento', 0):.2f}")

ok(f'Faturamento global inclui os R${TOTAL_ESPERADO:.2f} do novo atendimento',
   met.get('total_faturamento', 0) >= TOTAL_ESPERADO,
   f"total_global=R${met.get('total_faturamento', 0):.2f} >= R${TOTAL_ESPERADO}")

receita_7d = met.get('receita_7dias', [])
receita_hoje = next(
    (d['receita'] for d in receita_7d if d['data'] == date.today().isoformat()), 0
)
ok(f'Receita de hoje no gráfico 7 dias >= R${TOTAL_ESPERADO:.2f}',
   receita_hoje >= TOTAL_ESPERADO,
   f"receita_hoje=R${receita_hoje:.2f}")


# ══════════════════════════════════════════════════════════════════════════════
print('\n── Passo 17: Gestor — Relatório da Barbearia ────────────────')
# ══════════════════════════════════════════════════════════════════════════════
r = req('get', '/relatorios/resumo', token=S['gt'],
        params={'inicio': INICIO_REL, 'fim': FIM_REL})
rel = r.json() if r.ok else {}
ok('GET /relatorios/resumo retorna receita da barbearia',
   r.status_code == 200,
   f"atendimentos={rel.get('total_atendimentos')} "
   f"receita=R${rel.get('receita_total', 0):.2f} "
   f"ticket_medio=R${rel.get('ticket_medio', 0):.2f}")

ok(f'Receita da barbearia inclui R${TOTAL_ESPERADO:.2f} do atendimento',
   rel.get('receita_total', 0) >= TOTAL_ESPERADO,
   f"receita=R${rel.get('receita_total', 0):.2f} >= R${TOTAL_ESPERADO}")

# Verifica relatório por barbeiro
r = req('get', '/relatorios/por-barbeiro', token=S['gt'],
        params={'inicio': INICIO_REL, 'fim': FIM_REL})
lista_b = r.json() if r.ok else []
pedro_rel = next((b for b in lista_b if b.get('barbeiro_id') == S['barbeiro_id']), None)
ok(f'"{BARBEIRO_NOME}" aparece no relatório por barbeiro com comissão calculada',
   pedro_rel is not None,
   f"receita=R${pedro_rel.get('receita_gerada', 0) if pedro_rel else 0} "
   f"comissao=R${pedro_rel.get('comissao_calculada', 0) if pedro_rel else 0} (40%)")


# ── RESULTADO FINAL ────────────────────────────────────────────────────────────
print(f'\n{"="*64}')
total   = len(_resultados)
passou  = total - len(_falhas)
print(f'  RESULTADO: {passou}/{total} passos OK  |  {len(_falhas)} falha(s)')
print(f'{"="*64}\n')

print('  Resumo completo:')
for n, desc, ok_val, det in _resultados:
    sym = '✅' if ok_val else '❌'
    print(f"  {sym} {n:02d}. {desc}")
    if not ok_val and det:
        print(f"         Detalhe: {det}")

print()
if _falhas:
    print(f"  ❌ Passos com falha: {_falhas}")
    print(f'{"="*64}\n')
    sys.exit(1)
else:
    print(f"  🎉 TODOS OS {total} PASSOS PASSARAM!")
    print(f"     Fluxo E2E completo validado:")
    print(f"     Barbearia   : {BARB_NOME} (/{SLUG})")
    print(f"     Gestor      : {GESTOR_EMAIL}")
    print(f"     Barbeiro    : {BARBEIRO_EMAIL}")
    print(f"     Receita E2E : R${TOTAL_ESPERADO:.2f} (corte + pomada via PIX)")
    print(f"     Rotas fix   : GET /super/barbearias/lista ✔  GET /super/gestores/lista ✔")
    print(f'{"="*64}\n')
    sys.exit(0)
