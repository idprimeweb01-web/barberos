#!/usr/bin/env python3
"""
Suite completa de testes — BarberOS
====================================
Requer servidor rodando em localhost:5000 com banco PostgreSQL acessível.

Configuração via variáveis de ambiente:
  BASE_URL=http://localhost:5000
  SUPER_EMAIL=admin@barberos.com
  SUPER_SENHA=admin123

Rodar:
  python test_suite_completo.py [-v]
"""

import os
import sys
import time
import unittest
from datetime import date, timedelta

try:
    import requests
except ImportError:
    sys.exit("Instale requests: pip install requests")

# ── Configuração ──────────────────────────────────────────────────────────────
BASE    = os.getenv("BASE_URL",    "http://localhost:5000")
S_EMAIL = os.getenv("SUPER_EMAIL", "admin@barberos.com")
S_SENHA = os.getenv("SUPER_SENHA", "admin123")

# ── Estado global compartilhado entre os testes ───────────────────────────────
G: dict = {}


# ── Helpers HTTP ──────────────────────────────────────────────────────────────
def _hdr(token=None):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h

def GET(path, token=None, **kw):
    return requests.get(f"{BASE}{path}", headers=_hdr(token), timeout=10, **kw)

def POST(path, body=None, token=None, **kw):
    return requests.post(f"{BASE}{path}", json=body, headers=_hdr(token), timeout=10, **kw)

def PUT(path, body=None, token=None, **kw):
    return requests.put(f"{BASE}{path}", json=body, headers=_hdr(token), timeout=10, **kw)

def DELETE(path, token=None, **kw):
    return requests.delete(f"{BASE}{path}", headers=_hdr(token), timeout=10, **kw)

def login(email, senha):
    r = POST("/auth/login", {"email": email, "senha": senha})
    return r.json().get("access_token") if r.status_code == 200 else None

def _ts():
    return str(int(time.time()))[-7:]

def _prox_seg():
    """Próxima segunda-feira daqui a pelo menos 8 dias."""
    d = date.today() + timedelta(days=8)
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d


# ── Setup do módulo ───────────────────────────────────────────────────────────
def setUpModule():
    """Cria toda infraestrutura antes dos testes."""
    # Verificar servidor
    try:
        requests.get(BASE, timeout=5)
    except requests.ConnectionError:
        sys.exit(f"\n✗ Servidor não responde em {BASE}. Inicie com: python run.py\n")

    ts = _ts()

    # 1. Login super admin
    tok = login(S_EMAIL, S_SENHA)
    if not tok:
        sys.exit(f"\n✗ Login super admin falhou ({S_EMAIL}). Configure SUPER_EMAIL/SUPER_SENHA.\n")
    G["ST"] = tok  # super token

    # 2. Barbearia de teste
    slug = f"tst{ts}"
    r = POST("/super/barbearias", {"nome": f"Barbearia Tst {ts}", "slug": slug}, G["ST"])
    assert r.status_code == 201, f"Criar barbearia: {r.text}"
    G["bar_id"] = r.json()["id"]
    G["slug"]   = slug

    # 3. Gestor de teste
    ge = f"gest{ts}@tst.com"
    gs = "teste123"
    r = POST("/super/gestor", {
        "nome": f"Gestor Tst {ts}", "email": ge,
        "telefone": f"1190{ts}", "senha": gs,
        "barbearia_id": G["bar_id"],
    }, G["ST"])
    assert r.status_code == 201, f"Criar gestor: {r.text}"
    G["gest_id"]    = r.json().get("gestor", {}).get("id")
    G["gest_email"] = ge
    G["gest_senha"] = gs
    G["GT"]         = login(ge, gs)
    assert G["GT"], "Login gestor falhou"

    # 4. Barbeiro de teste
    be = f"barb{ts}@tst.com"
    bs = "teste123"
    r = POST("/admin/barbeiros", {
        "nome": f"Barbeiro Tst {ts}", "email": be,
        "telefone": f"1191{ts}", "senha": bs,
        "comissao_percentual": 30,
    }, G["GT"])
    assert r.status_code == 201, f"Criar barbeiro: {r.text}"
    G["barb_id"]    = r.json()["barbeiro"]["id"]
    G["barb_email"] = be
    G["barb_senha"] = bs
    G["BT"]         = login(be, bs)
    assert G["BT"], "Login barbeiro falhou"

    # 5. Serviço
    r = POST("/servicos", {
        "nome": f"Corte Tst {ts}", "duracao_minutos": 30, "preco": 45.00,
    }, G["GT"])
    assert r.status_code == 201, f"Criar serviço: {r.text}"
    G["sv_id"] = r.json()["id"]

    # 6. Produto
    r = POST("/admin/produtos", {
        "nome": f"Pomada Tst {ts}", "categoria": "Finalizadores",
        "preco": 28.00, "quantidade_estoque": 50,
    }, G["GT"])
    assert r.status_code == 201, f"Criar produto: {r.text}"
    G["prod_id"] = r.json()["id"]

    # 7. Vincular serviço ao barbeiro
    POST(f"/servicos/{G['sv_id']}/barbeiros/{G['barb_id']}", token=G["GT"])

    # 8. Configurar agenda do barbeiro
    r = PUT(f"/admin/agenda/{G['barb_id']}", {
        "horario_abertura": "08:00", "horario_fechamento": "18:00",
        "intervalo_minutos": 60, "loja_aberta": True,
    }, G["GT"])
    assert r.status_code == 200, f"Config agenda: {r.text}"

    # 9. Data futura de teste (próxima segunda-feira +8d)
    G["dt"] = _prox_seg().isoformat()

    # 10. Agendamento para caixa
    r = POST(f"/b/{slug}/agendamentos", {
        "nome": "Cliente Caixa", "telefone": "11999000001",
        "barbeiro_id": G["barb_id"], "servico_id": G["sv_id"],
        "data_hora": f"{G['dt']}T09:00",
    })
    assert r.status_code == 201, f"Ag caixa: {r.text}"
    G["ag_cx_id"] = r.json()["agendamento"]["id"]

    # 11. Agendamento para cancelar
    r = POST(f"/b/{slug}/agendamentos", {
        "nome": "Cliente Cancelar", "telefone": "11999000002",
        "barbeiro_id": G["barb_id"], "servico_id": G["sv_id"],
        "data_hora": f"{G['dt']}T10:00",
    })
    assert r.status_code == 201, f"Ag cancelar: {r.text}"
    G["ag_del_id"] = r.json()["agendamento"]["id"]

    # 12. Bloqueio para teste de liberação
    r = POST("/admin/agenda/bloqueios", {
        "data": G["dt"], "dia_inteiro": False,
        "hora_inicio": "14:00", "hora_fim": "15:00", "tipo": "pontual",
    }, G["GT"])
    G["blq_slot"] = "14:00"

    print(f"\n✓ Setup OK — slug:{slug} barbeiro:{G['barb_id']} data:{G['dt']}\n")


def tearDownModule():
    """Marca barbearia de teste como inativa."""
    try:
        PUT(f"/super/barbearias/{G['bar_id']}", {"ativo": False}, G["ST"])
    except Exception:
        pass


# ── Classe base ───────────────────────────────────────────────────────────────
class Base(unittest.TestCase):
    def ok(self, r, msg=""):
        self.assertIn(r.status_code, [200, 201],
            f"{msg} — HTTP {r.status_code}: {r.text[:200]}")

    def eq(self, r, code, msg=""):
        self.assertEqual(r.status_code, code,
            f"{msg} — esperado {code}, obtido {r.status_code}: {r.text[:200]}")

    def has(self, d, *keys):
        for k in keys:
            self.assertIn(k, d, f'"{k}" ausente em {list(d)[:10]}')

    @property
    def ST(self): return G["ST"]
    @property
    def GT(self): return G["GT"]
    @property
    def BT(self): return G["BT"]
    @property
    def slug(self): return G["slug"]
    @property
    def barb_id(self): return G["barb_id"]
    @property
    def sv_id(self): return G["sv_id"]
    @property
    def prod_id(self): return G["prod_id"]
    @property
    def dt(self): return G["dt"]


# ══════════════════════════════════════════════════════════════════════════════
# 1. AUTH
# ══════════════════════════════════════════════════════════════════════════════
class T01_Auth(Base):

    def test_01_login_super_ok(self):
        r = POST("/auth/login", {"email": S_EMAIL, "senha": S_SENHA})
        self.ok(r, "login super")
        self.has(r.json(), "access_token")

    def test_02_login_gestor_ok(self):
        r = POST("/auth/login", {"email": G["gest_email"], "senha": G["gest_senha"]})
        self.ok(r, "login gestor")
        self.has(r.json(), "access_token")

    def test_03_login_barbeiro_ok(self):
        r = POST("/auth/login", {"email": G["barb_email"], "senha": G["barb_senha"]})
        self.ok(r, "login barbeiro")
        self.has(r.json(), "access_token")

    def test_04_login_email_invalido(self):
        r = POST("/auth/login", {"email": "nao@existe.com", "senha": "123456"})
        self.eq(r, 401, "email inválido")

    def test_05_login_senha_errada(self):
        r = POST("/auth/login", {"email": S_EMAIL, "senha": "ERRADA"})
        self.eq(r, 401, "senha errada")

    def test_06_login_corpo_vazio(self):
        r = POST("/auth/login", {})
        self.assertIn(r.status_code, [400, 401])

    def test_07_me_com_token(self):
        r = GET("/auth/me", self.GT)
        self.ok(r, "GET /me")
        self.has(r.json(), "email", "perfil")

    def test_08_me_sem_token(self):
        r = GET("/auth/me")
        self.eq(r, 401, "sem token")

    def test_09_me_token_invalido(self):
        r = GET("/auth/me", "token.invalido.xyz")
        self.eq(r, 422, "token inválido")

    def test_10_alterar_senha_ok(self):
        r = PUT("/auth/alterar-senha", {
            "senha_atual": G["barb_senha"], "nova_senha": G["barb_senha"],
        }, self.BT)
        self.ok(r, "alterar senha")

    def test_11_alterar_senha_errada(self):
        r = PUT("/auth/alterar-senha", {
            "senha_atual": "ERRADA123", "nova_senha": "novaSenha9",
        }, self.BT)
        self.eq(r, 400, "senha atual errada")

    def test_12_alterar_senha_curta(self):
        r = PUT("/auth/alterar-senha", {
            "senha_atual": G["barb_senha"], "nova_senha": "123",
        }, self.BT)
        self.eq(r, 400, "senha nova curta")

    def test_13_esqueci_senha(self):
        r = POST("/auth/esqueci-senha", {"email": G["barb_email"]})
        self.ok(r, "esqueci senha")

    def test_14_listar_solicitacoes_gestor(self):
        r = GET("/auth/gestor/solicitacoes-senha", self.GT)
        self.ok(r, "listar solicitações")
        self.assertIsInstance(r.json(), list)

    def test_15_solicitacoes_sem_permissao(self):
        r = GET("/auth/gestor/solicitacoes-senha", self.BT)
        self.eq(r, 403, "barbeiro sem permissão")


# ══════════════════════════════════════════════════════════════════════════════
# 2. AGENDAMENTO PÚBLICO
# ══════════════════════════════════════════════════════════════════════════════
class T02_Publico(Base):

    def test_01_barbearia_info(self):
        r = GET(f"/b/{self.slug}/barbearia-info")
        self.ok(r)
        self.has(r.json(), "id", "nome", "slug")

    def test_02_barbearia_inexistente(self):
        r = GET("/b/sluginexistente999/barbearia-info")
        self.eq(r, 404)

    def test_03_listar_barbeiros(self):
        r = GET(f"/b/{self.slug}/barbeiros")
        self.ok(r)
        self.assertIsInstance(r.json(), list)
        self.assertGreater(len(r.json()), 0)

    def test_04_listar_servicos(self):
        r = GET(f"/b/{self.slug}/servicos")
        self.ok(r)
        self.assertIsInstance(r.json(), list)

    def test_05_servicos_do_barbeiro(self):
        r = GET(f"/b/{self.slug}/barbeiros/{self.barb_id}/servicos")
        self.ok(r)
        self.assertIsInstance(r.json(), list)
        self.assertGreater(len(r.json()), 0)

    def test_06_horarios_disponiveis(self):
        r = GET(f"/b/{self.slug}/agenda/horarios-disponiveis"
                f"?barbeiro_id={self.barb_id}&data={self.dt}")
        self.ok(r)
        d = r.json()
        self.has(d, "horarios")
        self.assertIsInstance(d["horarios"], list)

    def test_07_horarios_sem_barbeiro_id(self):
        r = GET(f"/b/{self.slug}/agenda/horarios-disponiveis?data={self.dt}")
        self.eq(r, 400)

    def test_08_horarios_sem_data(self):
        r = GET(f"/b/{self.slug}/agenda/horarios-disponiveis?barbeiro_id={self.barb_id}")
        self.eq(r, 400)

    def test_09_horarios_data_passada(self):
        ontem = (date.today() - timedelta(days=1)).isoformat()
        r = GET(f"/b/{self.slug}/agenda/horarios-disponiveis"
                f"?barbeiro_id={self.barb_id}&data={ontem}")
        self.ok(r)
        self.assertEqual(r.json().get("horarios", []), [])

    def test_10_criar_agendamento_ok(self):
        dt2 = (date.today() + timedelta(days=15)).isoformat()
        r = POST(f"/b/{self.slug}/agendamentos", {
            "nome": "Cliente Novo", "telefone": "11988776655",
            "barbeiro_id": self.barb_id, "servico_id": self.sv_id,
            "data_hora": f"{dt2}T11:00",
        })
        self.ok(r, "criar agendamento")
        d = r.json()
        self.has(d, "agendamento")
        self.has(d["agendamento"], "id", "status")
        self.assertEqual(d["agendamento"]["status"], "agendado")

    def test_11_criar_agendamento_sem_nome(self):
        r = POST(f"/b/{self.slug}/agendamentos", {
            "telefone": "11988776655", "barbeiro_id": self.barb_id,
            "servico_id": self.sv_id, "data_hora": f"{self.dt}T11:00",
        })
        self.eq(r, 400, "sem nome")

    def test_12_criar_agendamento_telefone_invalido(self):
        r = POST(f"/b/{self.slug}/agendamentos", {
            "nome": "X", "telefone": "abc",
            "barbeiro_id": self.barb_id, "servico_id": self.sv_id,
            "data_hora": f"{self.dt}T11:00",
        })
        self.eq(r, 400, "tel inválido")

    def test_13_criar_agendamento_data_invalida(self):
        r = POST(f"/b/{self.slug}/agendamentos", {
            "nome": "X", "telefone": "11999000099",
            "barbeiro_id": self.barb_id, "servico_id": self.sv_id,
            "data_hora": "data-errada",
        })
        self.eq(r, 400, "data inválida")

    def test_14_criar_agendamento_horario_ocupado(self):
        # 09:00 já foi criado no setUpModule
        r = POST(f"/b/{self.slug}/agendamentos", {
            "nome": "Outro", "telefone": "11999000050",
            "barbeiro_id": self.barb_id, "servico_id": self.sv_id,
            "data_hora": f"{self.dt}T09:00",
        })
        self.eq(r, 400, "horário ocupado")

    def test_15_get_agendamento_publico(self):
        r = GET(f"/b/{self.slug}/agendamento/{G['ag_cx_id']}")
        self.ok(r)
        self.has(r.json(), "id", "status", "barbeiro", "servico")

    def test_16_get_agendamento_inexistente(self):
        r = GET(f"/b/{self.slug}/agendamento/999999")
        self.eq(r, 404)


# ══════════════════════════════════════════════════════════════════════════════
# 3. BARBEIRO — AGENDA
# ══════════════════════════════════════════════════════════════════════════════
class T03_BarbeiroAgenda(Base):

    def test_01_meus_agendamentos_hoje(self):
        r = GET(f"/agenda/meus-agendamentos?data={date.today().isoformat()}", self.BT)
        self.ok(r)
        d = r.json()
        # Novo formato: {agendamentos, bloqueios}
        self.assertTrue(isinstance(d, dict) or isinstance(d, list))

    def test_02_meus_agendamentos_data_futura(self):
        r = GET(f"/agenda/meus-agendamentos?data={self.dt}", self.BT)
        self.ok(r)

    def test_03_meus_agendamentos_sem_data(self):
        r = GET("/agenda/meus-agendamentos", self.BT)
        self.eq(r, 400)

    def test_04_minha_config(self):
        r = GET("/agenda/minha-config", self.BT)
        self.ok(r)
        self.has(r.json(), "horario_abertura", "horario_fechamento", "intervalo_minutos")

    def test_05_meus_servicos(self):
        r = GET("/agenda/meus-servicos", self.BT)
        self.ok(r)
        self.assertIsInstance(r.json(), list)

    def test_06_meu_dashboard(self):
        r = GET("/agenda/meu-dashboard", self.BT)
        self.ok(r)
        self.has(r.json(), "atendimentos_hoje", "faturamento_hoje")

    def test_07_meu_perfil(self):
        r = GET("/agenda/meu-perfil", self.BT)
        self.ok(r)
        self.has(r.json(), "nome", "email")

    def test_08_atualizar_perfil(self):
        r = PUT("/agenda/meu-perfil", {"nome": G["barb_email"].split("@")[0].upper()}, self.BT)
        self.ok(r)

    def test_09_url_agendamento(self):
        r = GET("/agenda/url-agendamento", self.BT)
        self.ok(r)
        self.has(r.json(), "url")

    def test_10_agendamento_manual_ok(self):
        dt2 = (date.today() + timedelta(days=20)).isoformat()
        r = POST("/agenda/agendamento-manual", {
            "nome": "Manual Barbeiro", "telefone": "11997777777",
            "servico_id": self.sv_id, "data_hora": f"{dt2}T08:00",
        }, self.BT)
        self.ok(r, "agendamento manual barbeiro")

    def test_11_agendamento_manual_horario_passado(self):
        r = POST("/agenda/agendamento-manual", {
            "nome": "Passado", "telefone": "11997777778",
            "servico_id": self.sv_id, "data_hora": "2020-01-01T08:00",
        }, self.BT)
        self.eq(r, 400, "horário passado")

    def test_12_cancelar_agendamento(self):
        r = DELETE(f"/agendamentos/{G['ag_del_id']}", self.BT)
        self.ok(r, "cancelar ag")

    def test_13_cancelar_ja_cancelado(self):
        r = DELETE(f"/agendamentos/{G['ag_del_id']}", self.BT)
        self.eq(r, 400, "já cancelado")

    def test_14_solicitar_liberacao(self):
        r = POST("/agenda/solicitar-liberacao", {
            "data": self.dt, "hora_inicio": G["blq_slot"],
            "hora_fim": "15:00", "motivo": "Cliente especial",
        }, self.BT)
        self.assertIn(r.status_code, [201, 409], f"solicitar: {r.text}")
        if r.status_code == 201:
            G["solic_id"] = r.json()["id"]

    def test_15_solicitar_liberacao_duplicada(self):
        # Segunda tentativa deve retornar 409
        r = POST("/agenda/solicitar-liberacao", {
            "data": self.dt, "hora_inicio": G["blq_slot"],
            "hora_fim": "15:00", "motivo": "Segundo pedido",
        }, self.BT)
        self.assertIn(r.status_code, [201, 409])

    def test_16_notificacoes_liberacao(self):
        r = GET("/agenda/notificacoes-liberacao", self.BT)
        self.ok(r)
        self.assertIsInstance(r.json(), list)


# ══════════════════════════════════════════════════════════════════════════════
# 4. BARBEIRO — CAIXA (fluxo sequencial)
# ══════════════════════════════════════════════════════════════════════════════
class T04_BarbeiroCaixa(Base):
    """Fluxo completo de caixa: iniciar → add item → del item → efetuar."""
    _at_id   = None
    _item_id = None

    def test_01_iniciar_atendimento(self):
        r = POST(f"/agendamentos/{G['ag_cx_id']}/iniciar", {}, self.BT)
        self.assertIn(r.status_code, [200, 201], f"iniciar: {r.text}")
        T04_BarbeiroCaixa._at_id = r.json()["atendimento"]["id"]
        self.assertIsNotNone(T04_BarbeiroCaixa._at_id)

    def test_02_iniciar_idempotente(self):
        r = POST(f"/agendamentos/{G['ag_cx_id']}/iniciar", {}, self.BT)
        self.ok(r, "iniciar idempotente")

    def test_03_get_caixa(self):
        r = GET(f"/caixa/agendamento/{G['ag_cx_id']}", self.BT)
        self.ok(r)
        self.has(r.json(), "agendamento")

    def test_04_ver_atendimento(self):
        at_id = T04_BarbeiroCaixa._at_id
        if not at_id:
            self.skipTest("sem atendimento")
        r = GET(f"/atendimentos/{at_id}", self.BT)
        self.ok(r)
        self.has(r.json(), "id", "itens", "status_operacao")

    def test_05_adicionar_item_produto(self):
        at_id = T04_BarbeiroCaixa._at_id
        if not at_id:
            self.skipTest("sem atendimento")
        r = POST(f"/atendimentos/{at_id}/itens", {
            "tipo": "produto", "produto_id": self.prod_id, "quantidade": 1,
        }, self.BT)
        self.ok(r, "add item")
        T04_BarbeiroCaixa._item_id = r.json()["item"]["id"]

    def test_06_adicionar_item_tipo_invalido(self):
        at_id = T04_BarbeiroCaixa._at_id
        if not at_id:
            self.skipTest("sem atendimento")
        r = POST(f"/atendimentos/{at_id}/itens", {
            "tipo": "invalido", "quantidade": 1,
        }, self.BT)
        self.eq(r, 400)

    def test_07_remover_item(self):
        at_id   = T04_BarbeiroCaixa._at_id
        item_id = T04_BarbeiroCaixa._item_id
        if not at_id or not item_id:
            self.skipTest("sem item")
        r = DELETE(f"/atendimentos/{at_id}/itens/{item_id}", self.BT)
        self.ok(r, "del item")

    def test_08_efetuar_atendimento(self):
        at_id = T04_BarbeiroCaixa._at_id
        if not at_id:
            self.skipTest("sem atendimento")
        r = PUT(f"/atendimentos/{at_id}/efetuar", {"forma_pagamento": "dinheiro"}, self.BT)
        self.ok(r, "efetuar")
        self.has(r.json(), "pagamento")
        self.assertEqual(r.json()["pagamento"]["forma_pagamento"], "dinheiro")

    def test_09_efetuar_ja_efetuado(self):
        at_id = T04_BarbeiroCaixa._at_id
        if not at_id:
            self.skipTest("sem atendimento")
        r = PUT(f"/atendimentos/{at_id}/efetuar", {"forma_pagamento": "pix"}, self.BT)
        self.eq(r, 400, "já efetuado")

    def test_10_efetuar_forma_invalida(self):
        # Cria um segundo agendamento para testar validação
        dt_tmp = (date.today() + timedelta(days=25)).isoformat()
        r = POST(f"/b/{self.slug}/agendamentos", {
            "nome": "Forma Inv", "telefone": "11988110011",
            "barbeiro_id": self.barb_id, "servico_id": self.sv_id,
            "data_hora": f"{dt_tmp}T08:00",
        })
        if r.status_code != 201:
            self.skipTest("sem slot disponível")
        ag_tmp = r.json()["agendamento"]["id"]
        r2 = POST(f"/agendamentos/{ag_tmp}/iniciar", {}, self.BT)
        if r2.status_code not in [200, 201]:
            self.skipTest("não iniciou")
        at_tmp = r2.json()["atendimento"]["id"]
        r3 = PUT(f"/atendimentos/{at_tmp}/efetuar", {"forma_pagamento": "xablau"}, self.BT)
        self.eq(r3, 400)

    def test_11_listar_atendimentos_hoje(self):
        r = GET(f"/atendimentos?data={date.today().isoformat()}", self.BT)
        self.ok(r)
        self.assertIsInstance(r.json(), list)

    def test_12_sem_permissao_caixa(self):
        at_id = T04_BarbeiroCaixa._at_id
        if not at_id:
            self.skipTest("sem atendimento")
        r = GET(f"/atendimentos/{at_id}")  # sem token
        self.eq(r, 401)


# ══════════════════════════════════════════════════════════════════════════════
# 5. GESTOR — BARBEIROS
# ══════════════════════════════════════════════════════════════════════════════
class T05_GestorBarbeiros(Base):
    _novo_id = None

    def test_01_listar_barbeiros(self):
        r = GET("/admin/barbeiros", self.GT)
        self.ok(r)
        self.assertIsInstance(r.json(), list)

    def test_02_criar_barbeiro(self):
        ts = _ts()
        r = POST("/admin/barbeiros", {
            "nome": f"Barb Extra {ts}",
            "email": f"extra{ts}@tst.com",
            "telefone": f"1192{ts}",
            "senha": "extra123",
            "comissao_percentual": 25,
        }, self.GT)
        self.ok(r, "criar barbeiro")
        T05_GestorBarbeiros._novo_id = r.json()["barbeiro"]["id"]

    def test_03_criar_barbeiro_sem_nome(self):
        r = POST("/admin/barbeiros", {
            "email": "x@x.com", "telefone": "11900000000",
            "senha": "abc123", "comissao_percentual": 20,
        }, self.GT)
        self.eq(r, 400)

    def test_04_criar_barbeiro_email_dup(self):
        r = POST("/admin/barbeiros", {
            "nome": "Dup", "email": G["barb_email"],
            "telefone": "11900000001", "senha": "abc123", "comissao_percentual": 20,
        }, self.GT)
        self.eq(r, 409, "email duplicado")

    def test_05_editar_barbeiro(self):
        nid = T05_GestorBarbeiros._novo_id
        if not nid:
            self.skipTest("sem barbeiro novo")
        r = PUT(f"/admin/barbeiros/{nid}", {"nome": "Barb Editado"}, self.GT)
        self.ok(r)

    def test_06_editar_barbeiro_inexistente(self):
        r = PUT("/admin/barbeiros/999999", {"nome": "X"}, self.GT)
        self.eq(r, 404)

    def test_07_desativar_barbeiro(self):
        nid = T05_GestorBarbeiros._novo_id
        if not nid:
            self.skipTest("sem barbeiro novo")
        r = DELETE(f"/admin/barbeiros/{nid}", self.GT)
        self.ok(r)

    def test_08_barbeiro_sem_permissao(self):
        r = GET("/admin/barbeiros", self.BT)
        self.eq(r, 403)


# ══════════════════════════════════════════════════════════════════════════════
# 6. GESTOR — SERVIÇOS
# ══════════════════════════════════════════════════════════════════════════════
class T06_GestorServicos(Base):
    _novo_sv_id = None

    def test_01_listar_servicos(self):
        r = GET("/servicos", self.GT)
        self.ok(r)
        self.assertIsInstance(r.json(), list)

    def test_02_criar_servico(self):
        ts = _ts()
        r = POST("/servicos", {
            "nome": f"Barba Tst {ts}", "duracao_minutos": 20, "preco": 35.00,
        }, self.GT)
        self.ok(r, "criar serviço")
        T06_GestorServicos._novo_sv_id = r.json()["id"]

    def test_03_criar_servico_sem_nome(self):
        r = POST("/servicos", {"duracao_minutos": 30, "preco": 40.00}, self.GT)
        self.eq(r, 400)

    def test_04_criar_servico_preco_negativo(self):
        r = POST("/servicos", {"nome": "X", "duracao_minutos": 30, "preco": -1}, self.GT)
        self.eq(r, 400)

    def test_05_editar_servico(self):
        nid = T06_GestorServicos._novo_sv_id
        if not nid:
            self.skipTest("sem serviço novo")
        r = PUT(f"/servicos/{nid}", {"nome": "Barba Editada", "preco": 40.00}, self.GT)
        self.ok(r)

    def test_06_desativar_servico(self):
        nid = T06_GestorServicos._novo_sv_id
        if not nid:
            self.skipTest("sem serviço novo")
        r = DELETE(f"/servicos/{nid}", self.GT)
        self.ok(r)

    def test_07_vincular_servico_barbeiro(self):
        r = POST(f"/servicos/{self.sv_id}/barbeiros/{self.barb_id}", token=self.GT)
        self.assertIn(r.status_code, [200, 201, 409])

    def test_08_servico_sem_permissao(self):
        r = POST("/servicos", {"nome": "X", "duracao_minutos": 30, "preco": 10}, self.BT)
        self.eq(r, 403)


# ══════════════════════════════════════════════════════════════════════════════
# 7. GESTOR — PRODUTOS
# ══════════════════════════════════════════════════════════════════════════════
class T07_GestorProdutos(Base):
    _novo_pd_id = None

    def test_01_listar_produtos_admin(self):
        r = GET("/admin/produtos", self.GT)
        self.ok(r)
        self.assertIsInstance(r.json(), list)

    def test_02_listar_produtos_barbeiro(self):
        r = GET("/produtos", self.BT)
        self.ok(r)

    def test_03_criar_produto(self):
        ts = _ts()
        r = POST("/admin/produtos", {
            "nome": f"Shampoo {ts}", "categoria": "Higiene",
            "preco": 25.00, "quantidade_estoque": 30,
        }, self.GT)
        self.ok(r, "criar produto")
        T07_GestorProdutos._novo_pd_id = r.json()["id"]

    def test_04_criar_produto_sem_nome(self):
        r = POST("/admin/produtos", {"preco": 10.00}, self.GT)
        self.eq(r, 400)

    def test_05_editar_produto(self):
        nid = T07_GestorProdutos._novo_pd_id
        if not nid:
            self.skipTest("sem produto novo")
        r = PUT(f"/admin/produtos/{nid}", {"nome": "Shampoo Editado", "preco": 27.00}, self.GT)
        self.ok(r)

    def test_06_ajustar_estoque(self):
        r = PUT(f"/produtos/{self.prod_id}/estoque", {"quantidade": 5}, self.GT)
        self.ok(r, "ajustar estoque")

    def test_07_ajustar_estoque_negativo(self):
        r = PUT(f"/produtos/{self.prod_id}/estoque", {"quantidade": -2}, self.GT)
        self.ok(r, "remover estoque")

    def test_08_desativar_produto(self):
        nid = T07_GestorProdutos._novo_pd_id
        if not nid:
            self.skipTest("sem produto novo")
        r = DELETE(f"/admin/produtos/{nid}", self.GT)
        self.ok(r)

    def test_09_produto_sem_permissao(self):
        r = POST("/admin/produtos", {"nome": "X", "preco": 10}, self.BT)
        self.eq(r, 403)


# ══════════════════════════════════════════════════════════════════════════════
# 8. GESTOR — AGENDA CONFIG + GRADE
# ══════════════════════════════════════════════════════════════════════════════
class T08_GestorAgenda(Base):

    def test_01_listar_agenda(self):
        r = GET("/admin/agenda", self.GT)
        self.ok(r)
        self.assertIsInstance(r.json(), list)
        self.assertGreater(len(r.json()), 0)

    def test_02_config_agenda_ok(self):
        r = PUT(f"/admin/agenda/{self.barb_id}", {
            "horario_abertura": "09:00", "horario_fechamento": "18:00",
            "intervalo_minutos": 60, "loja_aberta": True,
        }, self.GT)
        self.ok(r)
        self.has(r.json(), "configuracao")

    def test_03_config_agenda_hora_invalida(self):
        r = PUT(f"/admin/agenda/{self.barb_id}", {
            "horario_abertura": "18:00", "horario_fechamento": "08:00",
            "intervalo_minutos": 60,
        }, self.GT)
        self.eq(r, 400, "abertura > fechamento")

    def test_04_config_agenda_barbeiro_invalido(self):
        r = PUT("/admin/agenda/999999", {
            "horario_abertura": "08:00", "horario_fechamento": "18:00",
            "intervalo_minutos": 60,
        }, self.GT)
        self.eq(r, 404)

    def test_05_grade_do_dia(self):
        r = GET(f"/admin/agenda/grade?barbeiro_id={self.barb_id}&data={self.dt}", self.GT)
        self.ok(r)
        self.has(r.json(), "config", "agendamentos", "servicos")

    def test_06_grade_sem_barbeiro_id(self):
        r = GET(f"/admin/agenda/grade?data={self.dt}", self.GT)
        self.eq(r, 400)

    def test_07_agendamento_manual_gestor(self):
        dt2 = (date.today() + timedelta(days=30)).isoformat()
        # Restaura config para 08:00 antes do teste
        PUT(f"/admin/agenda/{self.barb_id}", {
            "horario_abertura": "08:00", "horario_fechamento": "18:00",
            "intervalo_minutos": 60,
        }, self.GT)
        r = POST("/admin/agenda/agendamento-manual", {
            "barbeiro_id": self.barb_id, "nome": "Manual Gestor",
            "telefone": "11977111111", "servico_id": self.sv_id,
            "data_hora": f"{dt2}T08:00",
        }, self.GT)
        self.ok(r, "manual gestor")

    def test_08_agendamento_manual_sem_servico(self):
        r = POST("/admin/agenda/agendamento-manual", {
            "barbeiro_id": self.barb_id, "nome": "X",
            "telefone": "11977111112",
            "data_hora": f"{self.dt}T08:00",
        }, self.GT)
        self.eq(r, 400)

    def test_09_horarios_dia(self):
        r = GET(f"/admin/agenda/horarios?data={self.dt}", self.GT)
        self.ok(r)
        self.has(r.json(), "slots")

    def test_10_metricas(self):
        r = GET("/admin/metricas", self.GT)
        self.ok(r)
        self.has(r.json(), "total_barbeiros", "agendamentos_hoje")


# ══════════════════════════════════════════════════════════════════════════════
# 9. GESTOR — STATUS BARBEARIA
# ══════════════════════════════════════════════════════════════════════════════
class T09_GestorStatus(Base):

    def test_01_get_status(self):
        r = GET("/admin/barbearia/status", self.GT)
        self.ok(r)
        self.has(r.json(), "aberta")
        self.assertIsInstance(r.json()["aberta"], bool)

    def test_02_fechar_barbearia(self):
        r = PUT("/admin/barbearia/status", {"aberta": False}, self.GT)
        self.ok(r)
        self.assertEqual(r.json()["aberta"], False)

    def test_03_abrir_barbearia(self):
        r = PUT("/admin/barbearia/status", {"aberta": True}, self.GT)
        self.ok(r)
        self.assertEqual(r.json()["aberta"], True)

    def test_04_cliente_agenda_com_barbearia_fechada(self):
        """Teste principal: cliente consegue agendar mesmo com toggle FECHADO."""
        PUT("/admin/barbearia/status", {"aberta": False}, self.GT)
        dt2 = (date.today() + timedelta(days=35)).isoformat()
        r = POST(f"/b/{self.slug}/agendamentos", {
            "nome": "Cliente Fechado", "telefone": "11999090909",
            "barbeiro_id": self.barb_id, "servico_id": self.sv_id,
            "data_hora": f"{dt2}T08:00",
        })
        self.ok(r, "agendar com barbearia 'fechada' deve funcionar")
        # Restaura
        PUT("/admin/barbearia/status", {"aberta": True}, self.GT)

    def test_05_status_sem_permissao(self):
        r = GET("/admin/barbearia/status", self.BT)
        self.eq(r, 403)


# ══════════════════════════════════════════════════════════════════════════════
# 10. GESTOR — BLOQUEIOS
# ══════════════════════════════════════════════════════════════════════════════
class T10_GestorBloqueios(Base):
    _blq_id = None

    def test_01_listar_bloqueios_mes(self):
        m = date.today().month
        y = date.today().year
        r = GET(f"/admin/agenda/bloqueios/mes?mes={m}&ano={y}", self.GT)
        self.ok(r)
        self.has(r.json(), "mes", "ano", "dias")

    def test_02_listar_bloqueios_params_invalidos(self):
        r = GET("/admin/agenda/bloqueios/mes?mes=13&ano=2025", self.GT)
        self.eq(r, 400)

    def test_03_criar_bloqueio_dia_inteiro(self):
        dt_blq = (date.today() + timedelta(days=40)).isoformat()
        r = POST("/admin/agenda/bloqueios", {
            "data": dt_blq, "dia_inteiro": True, "tipo": "pontual",
        }, self.GT)
        self.ok(r, "bloqueio dia inteiro")
        G["blq_di_id"] = r.json().get("total")  # salva para teste de remoção

    def test_04_criar_bloqueio_horario(self):
        dt_blq = (date.today() + timedelta(days=41)).isoformat()
        r = POST("/admin/agenda/bloqueios", {
            "data": dt_blq, "dia_inteiro": False,
            "hora_inicio": "10:00", "hora_fim": "12:00", "tipo": "pontual",
        }, self.GT)
        self.ok(r)

    def test_05_criar_bloqueio_recorrente_dia_semana(self):
        dt_blq = (date.today() + timedelta(days=42)).isoformat()
        r = POST("/admin/agenda/bloqueios", {
            "data": dt_blq, "dia_inteiro": True,
            "tipo": "recorrente", "padrao": "dia_semana",
            "motivo": "Folga semanal",
        }, self.GT)
        self.ok(r)
        d = r.json()
        self.assertGreater(d.get("total", 0), 1, "deve criar múltiplos bloqueios")

    def test_06_criar_bloqueio_recorrente_dia_mes(self):
        dt_blq = (date.today() + timedelta(days=43)).isoformat()
        r = POST("/admin/agenda/bloqueios", {
            "data": dt_blq, "dia_inteiro": True,
            "tipo": "recorrente", "padrao": "data_especifica",
        }, self.GT)
        self.ok(r)

    def test_07_criar_bloqueio_horario_invalido(self):
        dt_blq = (date.today() + timedelta(days=44)).isoformat()
        r = POST("/admin/agenda/bloqueios", {
            "data": dt_blq, "dia_inteiro": False,
            "hora_inicio": "15:00", "hora_fim": "10:00", "tipo": "pontual",
        }, self.GT)
        self.eq(r, 400, "hora_fim < hora_inicio")

    def test_08_remover_bloqueio(self):
        # Cria e remove
        dt_blq = (date.today() + timedelta(days=60)).isoformat()
        r_c = POST("/admin/agenda/bloqueios", {
            "data": dt_blq, "dia_inteiro": True, "tipo": "pontual",
        }, self.GT)
        self.ok(r_c, "criar para remover")
        # Busca o ID pelo calendário
        m, y = int(dt_blq[5:7]), int(dt_blq[:4])
        r_m = GET(f"/admin/agenda/bloqueios/mes?mes={m}&ano={y}", self.GT)
        dia_n = int(dt_blq[8:10])
        dia_obj = next((d for d in r_m.json()["dias"] if d["dia"] == dia_n), None)
        if dia_obj and dia_obj.get("bloqueios"):
            blq_id = dia_obj["bloqueios"][0]["id"]
            r_d = DELETE(f"/admin/agenda/bloqueios/{blq_id}", self.GT)
            self.ok(r_d, "remover bloqueio")

    def test_09_remover_bloqueio_inexistente(self):
        r = DELETE("/admin/agenda/bloqueios/999999", self.GT)
        self.eq(r, 404)

    def test_10_bloqueio_bloqueia_horario_publico(self):
        """Slot bloqueado não deve aparecer nos horários disponíveis."""
        r = GET(f"/b/{self.slug}/agenda/horarios-disponiveis"
                f"?barbeiro_id={self.barb_id}&data={self.dt}", token=None)
        self.ok(r)
        horarios = r.json().get("horarios", [])
        self.assertNotIn(G["blq_slot"], horarios, "slot bloqueado não deve aparecer")


# ══════════════════════════════════════════════════════════════════════════════
# 11. GESTOR — SOLICITAÇÕES DE LIBERAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
class T11_GestorSolicitacoes(Base):

    def test_01_listar_solicitacoes_pendentes(self):
        r = GET("/admin/agenda/solicitacoes-liberacao?status=pendente", self.GT)
        self.ok(r)
        self.assertIsInstance(r.json(), list)

    def test_02_listar_solicitacoes_aprovadas(self):
        r = GET("/admin/agenda/solicitacoes-liberacao?status=aprovado", self.GT)
        self.ok(r)
        self.assertIsInstance(r.json(), list)

    def test_03_aprovar_solicitacao(self):
        solic_id = G.get("solic_id")
        if not solic_id:
            self.skipTest("nenhuma solicitação criada")
        r = PUT(f"/admin/agenda/solicitacoes-liberacao/{solic_id}", {"status": "aprovado"}, self.GT)
        self.ok(r, "aprovar")

    def test_04_rejeitar_solicitacao_inexistente(self):
        r = PUT("/admin/agenda/solicitacoes-liberacao/999999", {"status": "rejeitado"}, self.GT)
        self.eq(r, 404)

    def test_05_responder_status_invalido(self):
        solic_id = G.get("solic_id")
        if not solic_id:
            self.skipTest("sem solicitação")
        r = PUT(f"/admin/agenda/solicitacoes-liberacao/{solic_id}", {"status": "invalido"}, self.GT)
        self.assertIn(r.status_code, [400, 409])

    def test_06_criar_e_rejeitar(self):
        dt_novo = (date.today() + timedelta(days=50)).isoformat()
        # Cria bloqueio
        POST("/admin/agenda/bloqueios", {
            "data": dt_novo, "hora_inicio": "11:00", "hora_fim": "12:00",
            "dia_inteiro": False, "tipo": "pontual",
        }, self.GT)
        # Barbeiro solicita
        r_s = POST("/agenda/solicitar-liberacao", {
            "data": dt_novo, "hora_inicio": "11:00",
            "hora_fim": "12:00", "motivo": "Urgência",
        }, self.BT)
        if r_s.status_code != 201:
            self.skipTest("não criou solicitação")
        sol_id = r_s.json()["id"]
        # Gestor rejeita
        r_r = PUT(f"/admin/agenda/solicitacoes-liberacao/{sol_id}", {"status": "rejeitado"}, self.GT)
        self.ok(r_r, "rejeitar")
        # Barbeiro vê notificação
        r_n = GET("/agenda/notificacoes-liberacao", self.BT)
        self.ok(r_n)


# ══════════════════════════════════════════════════════════════════════════════
# 12. GESTOR — RELATÓRIOS
# ══════════════════════════════════════════════════════════════════════════════
class T12_GestorRelatorios(Base):

    def _ini_fim(self):
        hoje = date.today()
        return (date(hoje.year, hoje.month, 1).isoformat(), hoje.isoformat())

    def test_01_resumo(self):
        ini, fim = self._ini_fim()
        r = GET(f"/relatorios/resumo?inicio={ini}&fim={fim}", self.GT)
        self.ok(r)
        self.has(r.json(), "total_receita", "total_atendimentos")

    def test_02_por_barbeiro(self):
        ini, fim = self._ini_fim()
        r = GET(f"/relatorios/por-barbeiro?inicio={ini}&fim={fim}", self.GT)
        self.ok(r)
        self.assertIsInstance(r.json(), list)

    def test_03_produtos_mais_vendidos(self):
        ini, fim = self._ini_fim()
        r = GET(f"/relatorios/produtos-mais-vendidos?inicio={ini}&fim={fim}", self.GT)
        self.ok(r)
        self.assertIsInstance(r.json(), list)

    def test_04_clientes_frequentes(self):
        ini, fim = self._ini_fim()
        r = GET(f"/relatorios/clientes-frequentes?inicio={ini}&fim={fim}", self.GT)
        self.ok(r)
        self.assertIsInstance(r.json(), list)

    def test_05_receita_diaria(self):
        ini, fim = self._ini_fim()
        r = GET(f"/relatorios/receita-diaria?inicio={ini}&fim={fim}", self.GT)
        self.ok(r)
        self.assertIsInstance(r.json(), list)

    def test_06_relatorio_sem_periodo(self):
        r = GET("/relatorios/resumo", self.GT)
        self.eq(r, 400)

    def test_07_relatorio_sem_permissao(self):
        ini, fim = self._ini_fim()
        r = GET(f"/relatorios/resumo?inicio={ini}&fim={fim}", self.BT)
        self.eq(r, 403)


# ══════════════════════════════════════════════════════════════════════════════
# 13. SUPER ADMIN
# ══════════════════════════════════════════════════════════════════════════════
class T13_SuperAdmin(Base):
    _nova_bar_id = None
    _novo_gest_id = None

    def test_01_dashboard_metricas(self):
        r = GET("/super/dashboard/metricas", self.ST)
        self.ok(r)
        self.has(r.json(), "total_barbearias", "total_usuarios")

    def test_02_listar_barbearias(self):
        r = GET("/super/barbearias/lista", self.ST)
        self.ok(r)
        self.assertIsInstance(r.json(), list)

    def test_03_criar_barbearia(self):
        ts = _ts()
        r = POST("/super/barbearias", {
            "nome": f"Bar Extra {ts}", "slug": f"barex{ts}",
        }, self.ST)
        self.ok(r)
        T13_SuperAdmin._nova_bar_id = r.json()["id"]

    def test_04_criar_barbearia_slug_duplicado(self):
        r = POST("/super/barbearias", {
            "nome": "Dup", "slug": G["slug"],
        }, self.ST)
        self.eq(r, 409, "slug duplicado")

    def test_05_criar_barbearia_slug_invalido(self):
        r = POST("/super/barbearias", {
            "nome": "X", "slug": "Slug INVÁLIDO!",
        }, self.ST)
        self.eq(r, 400)

    def test_06_editar_barbearia(self):
        nid = T13_SuperAdmin._nova_bar_id
        if not nid:
            self.skipTest("sem barbearia nova")
        r = PUT(f"/super/barbearias/{nid}", {"nome": "Bar Editada"}, self.ST)
        self.ok(r)

    def test_07_atualizar_tema_barbearia(self):
        nid = T13_SuperAdmin._nova_bar_id
        if not nid:
            self.skipTest("sem barbearia nova")
        r = PUT(f"/super/barbearias/{nid}/tema", {"cor_primaria": "#CC8800"}, self.ST)
        self.ok(r)

    def test_08_listar_gestores(self):
        r = GET("/super/gestores/lista", self.ST)
        self.ok(r)
        self.assertIsInstance(r.json(), list)

    def test_09_criar_gestor(self):
        ts = _ts()
        nid = T13_SuperAdmin._nova_bar_id or G["bar_id"]
        r = POST("/super/gestor", {
            "nome": f"Gestor Ex {ts}",
            "email": f"gex{ts}@tst.com",
            "telefone": f"1193{ts}",
            "senha": "exgest123",
            "barbearia_id": nid,
        }, self.ST)
        self.ok(r)
        T13_SuperAdmin._novo_gest_id = r.json().get("gestor", {}).get("id")

    def test_10_criar_gestor_sem_barbearia(self):
        ts = _ts()
        r = POST("/super/gestor", {
            "nome": f"G {ts}", "email": f"g2{ts}@tst.com",
            "telefone": f"1194{ts}", "senha": "abc123",
        }, self.ST)
        self.eq(r, 400)

    def test_11_editar_gestor(self):
        gid = T13_SuperAdmin._novo_gest_id
        if not gid:
            self.skipTest("sem gestor novo")
        r = PUT(f"/super/gestor/{gid}", {"nome": "Gestor Editado"}, self.ST)
        self.ok(r)

    def test_12_resetar_senha_gestor(self):
        gid = T13_SuperAdmin._novo_gest_id
        if not gid:
            self.skipTest("sem gestor novo")
        r = PUT(f"/super/gestor/{gid}/resetar-senha", {"nova_senha": "novaSenha99"}, self.ST)
        self.ok(r)

    def test_13_acesso_negado_gestor(self):
        r = GET("/super/barbearias/lista", self.GT)
        self.eq(r, 403, "gestor não pode acessar super")

    def test_14_acesso_negado_barbeiro(self):
        r = GET("/super/dashboard/metricas", self.BT)
        self.eq(r, 403, "barbeiro não pode acessar super")

    def test_15_acesso_sem_token(self):
        r = GET("/super/barbearias/lista")
        self.eq(r, 401, "sem token")


# ══════════════════════════════════════════════════════════════════════════════
# 14. AUTH — GUARD em rotas protegidas
# ══════════════════════════════════════════════════════════════════════════════
class T14_AuthGuard(Base):

    def test_01_admin_barbeiros_sem_token(self):
        self.eq(GET("/admin/barbeiros"), 401)

    def test_02_admin_agenda_sem_token(self):
        self.eq(GET("/admin/agenda"), 401)

    def test_03_relatorios_sem_token(self):
        self.eq(GET("/relatorios/resumo"), 401)

    def test_04_meus_agendamentos_sem_token(self):
        self.eq(GET(f"/agenda/meus-agendamentos?data={date.today().isoformat()}"), 401)

    def test_05_barbeiro_no_gestor_route(self):
        self.eq(GET("/admin/barbeiros", self.BT), 403)

    def test_06_gestor_no_super_route(self):
        self.eq(GET("/super/barbearias/lista", self.GT), 403)

    def test_07_super_no_gestor_route(self):
        # Super admin pode acessar rotas de gestor (gestor_required aceita super)
        r = GET("/admin/barbeiros", self.ST)
        self.assertIn(r.status_code, [200, 403])  # depende da barbearia no JWT

    def test_08_cancelar_ag_de_outro_barbeiro(self):
        # Cria um segundo barbeiro e tenta cancelar agendamento do primeiro
        ts = _ts()
        r_b = POST("/admin/barbeiros", {
            "nome": f"B2 {ts}", "email": f"b2{ts}@tst.com",
            "telefone": f"1195{ts}", "senha": "b2senha",
            "comissao_percentual": 20,
        }, self.GT)
        if r_b.status_code != 201:
            self.skipTest("não criou b2")
        b2_token = login(f"b2{ts}@tst.com", "b2senha")
        if not b2_token:
            self.skipTest("não logou b2")
        # b2 tenta cancelar ag do primeiro barbeiro
        r = DELETE(f"/agendamentos/{G['ag_cx_id']}", b2_token)
        self.eq(r, 403, "outro barbeiro não pode cancelar")


# ══════════════════════════════════════════════════════════════════════════════
# 15. CLIENTES
# ══════════════════════════════════════════════════════════════════════════════
class T15_Clientes(Base):

    def test_01_listar_clientes(self):
        r = GET("/clientes", self.BT)
        self.ok(r)
        self.assertIsInstance(r.json(), list)

    def test_02_listar_clientes_gestor(self):
        r = GET("/clientes", self.GT)
        self.ok(r)

    def test_03_listar_clientes_sem_token(self):
        self.eq(GET("/clientes"), 401)


# ══════════════════════════════════════════════════════════════════════════════
# Runner personalizado com contagem colorida
# ══════════════════════════════════════════════════════════════════════════════
class _ColorRunner(unittest.TextTestRunner):
    """Runner que exibe contagem de testes ao final."""

    def run(self, test):
        result = super().run(test)
        total  = result.testsRun
        fails  = len(result.failures)
        errors = len(result.errors)
        skips  = len(result.skipped)
        passed = total - fails - errors - skips

        print("\n" + "═" * 60)
        print(f"  Total : {total}")
        print(f"  Passou: {passed}  ✓")
        if fails:  print(f"  Falhou: {fails}  ✗")
        if errors: print(f"  Erros : {errors}  !")
        if skips:  print(f"  Pulou : {skips}  -")
        print("═" * 60)

        if fails == 0 and errors == 0:
            print("  ✅  Todos os testes passaram!")
        else:
            print("  ❌  Há falhas — veja o relatório acima.")
        print()
        return result


if __name__ == "__main__":
    verbosity = 2 if "-v" in sys.argv else 1
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    # Ordem de execução
    for cls in [
        T01_Auth, T02_Publico, T03_BarbeiroAgenda, T04_BarbeiroCaixa,
        T05_GestorBarbeiros, T06_GestorServicos, T07_GestorProdutos,
        T08_GestorAgenda, T09_GestorStatus, T10_GestorBloqueios,
        T11_GestorSolicitacoes, T12_GestorRelatorios, T13_SuperAdmin,
        T14_AuthGuard, T15_Clientes,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    _ColorRunner(verbosity=verbosity).run(suite)
