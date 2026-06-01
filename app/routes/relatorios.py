from datetime import datetime, timedelta, date as date_cls
from flask import Blueprint, request, jsonify
from sqlalchemy import func, cast, Date
from app import db
from app.models import (
    Barbearia, Usuario, Barbeiro, Cliente, Servico, Produto,
    Atendimento, AtendimentoItem, Agendamento, AgendamentoServico,
)
from app.utils import get_barbearia_atual
from app.routes.auth import gestor_required, super_admin_required

relatorios = Blueprint('relatorios', __name__)

admin_required = gestor_required


def _erro(msg, code=400):
    return jsonify({'erro': msg}), code


# ── Helpers de período ────────────────────────────────────────────────────────

def _calcular_periodo(tipo, ref):
    if tipo == 'dia':
        ini = datetime(ref.year, ref.month, ref.day)
        fim = ini + timedelta(days=1)
    elif tipo == 'semana':
        monday = ref - timedelta(days=ref.weekday())
        ini = datetime(monday.year, monday.month, monday.day)
        fim = ini + timedelta(days=7)
    elif tipo == 'mes':
        ini = datetime(ref.year, ref.month, 1)
        if ref.month == 12:
            fim = datetime(ref.year + 1, 1, 1)
        else:
            fim = datetime(ref.year, ref.month + 1, 1)
    else:  # ano
        ini = datetime(ref.year, 1, 1)
        fim = datetime(ref.year + 1, 1, 1)
    return ini, fim


def _calcular_periodo_anterior(tipo, ini):
    if tipo == 'dia':
        ini_ant = ini - timedelta(days=1)
        fim_ant = ini
    elif tipo == 'semana':
        ini_ant = ini - timedelta(days=7)
        fim_ant = ini
    elif tipo == 'mes':
        if ini.month == 1:
            ini_ant = datetime(ini.year - 1, 12, 1)
        else:
            ini_ant = datetime(ini.year, ini.month - 1, 1)
        fim_ant = ini
    else:  # ano
        ini_ant = datetime(ini.year - 1, 1, 1)
        fim_ant = ini
    return ini_ant, fim_ant


def _variacao(atual, anterior):
    if not anterior:
        return None
    return round((atual - anterior) / anterior * 100, 1)


# ── Cálculo central ───────────────────────────────────────────────────────────

def _make_relatorio(barbearia_id, ini, fim, ini_ant, fim_ant, barbeiro_id=None):
    """Retorna dicionário com todas as métricas do período."""

    def at_filt(i, f):
        fl = [Atendimento.status_operacao == 'efetuado',
              Atendimento.criado_em >= i, Atendimento.criado_em < f]
        if barbearia_id:
            fl.append(Atendimento.barbearia_id == barbearia_id)
        if barbeiro_id:
            fl.append(Atendimento.barbeiro_id == barbeiro_id)
        return fl

    def ag_filt(i, f, status=None):
        fl = [Agendamento.data_hora >= i, Agendamento.data_hora < f]
        if barbearia_id:
            fl.append(Agendamento.barbearia_id == barbearia_id)
        if barbeiro_id:
            fl.append(Agendamento.barbeiro_id == barbeiro_id)
        if status:
            fl.append(Agendamento.status == status)
        return fl

    # ── Faturamento ───────────────────────────────────────────────
    fat_atual = float(db.session.query(func.sum(Atendimento.total))
                      .filter(*at_filt(ini, fim)).scalar() or 0)
    fat_ant   = float(db.session.query(func.sum(Atendimento.total))
                      .filter(*at_filt(ini_ant, fim_ant)).scalar() or 0)

    # ── Atendimentos / agendamentos ───────────────────────────────
    ag_conc = db.session.query(func.count(Agendamento.id)).filter(*ag_filt(ini, fim, 'concluido')).scalar() or 0
    ag_canc = db.session.query(func.count(Agendamento.id)).filter(*ag_filt(ini, fim, 'cancelado')).scalar() or 0
    ag_agend = db.session.query(func.count(Agendamento.id)).filter(*ag_filt(ini, fim, 'agendado')).scalar() or 0

    n_ef = db.session.query(func.count(Atendimento.id)).filter(*at_filt(ini, fim)).scalar() or 0
    ticket = round(fat_atual / n_ef, 2) if n_ef else 0.0

    # ── Por barbeiro ──────────────────────────────────────────────
    barb_rows = (
        db.session.query(
            Barbeiro.id, Usuario.nome, Barbeiro.comissao_percentual,
            func.count(Atendimento.id).label('ats'),
            func.sum(Atendimento.total).label('rec'),
        )
        .join(Usuario, Barbeiro.usuario_id == Usuario.id)
        .join(Atendimento, Atendimento.barbeiro_id == Barbeiro.id)
        .filter(*at_filt(ini, fim))
        .group_by(Barbeiro.id, Usuario.nome, Barbeiro.comissao_percentual)
        .order_by(func.sum(Atendimento.total).desc())
        .limit(10).all()
    )
    barbeiros = [
        {
            'id': bid, 'nome': nome,
            'atendimentos': int(ats or 0),
            'receita': float(rec or 0),
            'comissao_pct': float(com),
            'comissao': round(float(rec or 0) * float(com) / 100, 2),
        }
        for bid, nome, com, ats, rec in barb_rows
    ]

    # ── Serviços top 5 ────────────────────────────────────────────
    sv_rows = (
        db.session.query(
            Servico.nome,
            func.sum(AtendimentoItem.quantidade).label('qtd'),
            func.sum(AtendimentoItem.preco_unitario * AtendimentoItem.quantidade).label('rec'),
        )
        .join(AtendimentoItem, AtendimentoItem.servico_id == Servico.id)
        .join(Atendimento, Atendimento.id == AtendimentoItem.atendimento_id)
        .filter(AtendimentoItem.tipo == 'servico', *at_filt(ini, fim))
        .group_by(Servico.nome)
        .order_by(func.sum(AtendimentoItem.quantidade).desc())
        .limit(5).all()
    )
    servicos_top = [
        {'nome': n, 'quantidade': int(q or 0), 'receita': float(r or 0)}
        for n, q, r in sv_rows
    ]

    # ── Produtos top 5 ────────────────────────────────────────────
    pd_rows = (
        db.session.query(
            Produto.nome,
            func.sum(AtendimentoItem.quantidade).label('qtd'),
            func.sum(AtendimentoItem.preco_unitario * AtendimentoItem.quantidade).label('rec'),
        )
        .join(AtendimentoItem, AtendimentoItem.produto_id == Produto.id)
        .join(Atendimento, Atendimento.id == AtendimentoItem.atendimento_id)
        .filter(AtendimentoItem.tipo == 'produto', *at_filt(ini, fim))
        .group_by(Produto.nome)
        .order_by(func.sum(AtendimentoItem.quantidade).desc())
        .limit(5).all()
    )
    produtos_top = [
        {'nome': n, 'quantidade': int(q or 0), 'receita': float(r or 0)}
        for n, q, r in pd_rows
    ]

    # ── Estoque baixo (snapshot atual) ────────────────────────────
    est_q = Produto.query.filter(Produto.ativo == True, Produto.quantidade_estoque < 5)
    if barbearia_id:
        est_q = est_q.filter(Produto.barbearia_id == barbearia_id)
    estoque_baixo = [
        {'id': p.id, 'nome': p.nome, 'estoque': p.quantidade_estoque}
        for p in est_q.order_by(Produto.quantidade_estoque).limit(10).all()
    ]

    # ── Clientes top 5 ────────────────────────────────────────────
    cli_rows = (
        db.session.query(
            Cliente.nome,
            func.count(Atendimento.id).label('visitas'),
            func.sum(Atendimento.total).label('gasto'),
        )
        .join(Atendimento, Atendimento.cliente_id == Cliente.id)
        .filter(*at_filt(ini, fim))
        .group_by(Cliente.id, Cliente.nome)
        .order_by(func.count(Atendimento.id).desc())
        .limit(5).all()
    )
    clientes_top = [
        {'nome': n, 'visitas': int(v or 0), 'gasto': float(g or 0)}
        for n, v, g in cli_rows
    ]

    # ── Receita para gráfico ──────────────────────────────────────
    periodo_dias = (fim - ini).days
    if periodo_dias > 31:
        # Agrupar por mês
        grupo = cast(func.date_trunc('month', Atendimento.criado_em), Date)
        fmt_g = 'mes'
    else:
        # Agrupar por dia
        grupo = cast(Atendimento.criado_em, Date)
        fmt_g = 'dia'

    graf_rows = (
        db.session.query(grupo.label('p'), func.sum(Atendimento.total).label('r'))
        .filter(*at_filt(ini, fim))
        .group_by(grupo).order_by(grupo).all()
    )
    receita_grafico = [{'data': str(d), 'receita': float(r or 0)} for d, r in graf_rows]

    return {
        'periodo': {
            'inicio': ini.date().isoformat(),
            'fim': (fim - timedelta(seconds=1)).date().isoformat(),
        },
        'faturamento': {
            'total': fat_atual,
            'anterior': fat_ant,
            'variacao_pct': _variacao(fat_atual, fat_ant),
        },
        'atendimentos': {
            'concluidos': int(ag_conc),
            'cancelados':  int(ag_canc),
            'agendados':   int(ag_agend),
            'total':       int(ag_conc + ag_canc + ag_agend),
        },
        'ticket_medio': ticket,
        'barbeiros': barbeiros,
        'servicos_top': servicos_top,
        'produtos_top': produtos_top,
        'estoque_baixo': estoque_baixo,
        'clientes_top': clientes_top,
        'receita_grafico': receita_grafico,
        'receita_grafico_fmt': fmt_g,
    }


def _handle_periodo(barbearia_id):
    tipo     = request.args.get('tipo', 'mes').lower()
    data_str = request.args.get('data', '').strip()
    barb_id  = request.args.get('barbeiro_id', type=int)

    if tipo not in ('dia', 'semana', 'mes', 'ano'):
        return _erro('"tipo" deve ser dia, semana, mes ou ano.')

    ref = date_cls.today()
    if data_str:
        try:
            ref = datetime.strptime(data_str, '%Y-%m-%d').date()
        except ValueError:
            return _erro('Formato de data inválido. Use YYYY-MM-DD.')

    ini, fim     = _calcular_periodo(tipo, ref)
    ini_ant, fim_ant = _calcular_periodo_anterior(tipo, ini)

    resultado = _make_relatorio(barbearia_id, ini, fim, ini_ant, fim_ant, barb_id)
    resultado['tipo'] = tipo
    resultado['data_referencia'] = ref.isoformat()
    return jsonify(resultado)


# ── Rotas gestor ──────────────────────────────────────────────────────────────

@relatorios.get('/admin/relatorios/periodo')
@gestor_required
def relatorio_periodo_gestor():
    return _handle_periodo(get_barbearia_atual())


# ── Rotas super admin ─────────────────────────────────────────────────────────

@relatorios.get('/super/relatorios/periodo')
@super_admin_required
def relatorio_periodo_super():
    barbearia_id = request.args.get('barbearia_id', type=int)
    result = _handle_periodo(barbearia_id)

    # Adiciona comparativo por barbearia
    tipo     = request.args.get('tipo', 'mes').lower()
    data_str = request.args.get('data', '').strip()
    ref = date_cls.today()
    if data_str:
        try:
            ref = datetime.strptime(data_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    ini, fim = _calcular_periodo(tipo if tipo in ('dia','semana','mes','ano') else 'mes', ref)

    bar_rows = (
        db.session.query(
            Barbearia.id, Barbearia.nome,
            func.count(Atendimento.id).label('ats'),
            func.sum(Atendimento.total).label('rec'),
        )
        .join(Atendimento, Atendimento.barbearia_id == Barbearia.id)
        .filter(
            Atendimento.status_operacao == 'efetuado',
            Atendimento.criado_em >= ini,
            Atendimento.criado_em < fim,
        )
        .group_by(Barbearia.id, Barbearia.nome)
        .order_by(func.sum(Atendimento.total).desc())
        .all()
    )
    # Inject barbearias array into the response JSON
    import json as _json
    body = result.get_json()
    body['barbearias'] = [
        {
            'id': bid, 'nome': nome,
            'atendimentos': int(ats or 0),
            'faturamento': float(rec or 0),
            'ticket_medio': round(float(rec or 0) / int(ats or 1), 2) if ats else 0.0,
        }
        for bid, nome, ats, rec in bar_rows
    ]
    return jsonify(body)


# ── Rotas legadas (mantidas para compat) ──────────────────────────────────────

def _filtro_periodo(inicio, fim, barbearia_id):
    return (
        Atendimento.barbearia_id    == barbearia_id,
        Atendimento.status_operacao == 'efetuado',
        Atendimento.criado_em       >= inicio,
        Atendimento.criado_em       < fim,
    )


@relatorios.get('/relatorios/resumo')
@admin_required
def resumo():
    barbearia_id = get_barbearia_atual()
    inicio_str = request.args.get('inicio', '').strip()
    fim_str    = request.args.get('fim', '').strip()
    if not inicio_str or not fim_str:
        return _erro('Parâmetros "inicio" e "fim" são obrigatórios.')
    try:
        inicio = datetime.strptime(inicio_str, '%Y-%m-%d')
        fim    = datetime.strptime(fim_str,    '%Y-%m-%d') + timedelta(days=1)
    except ValueError:
        return _erro('Formato inválido. Use YYYY-MM-DD.')

    total = db.session.query(func.count(Atendimento.id)).filter(
        *_filtro_periodo(inicio, fim, barbearia_id)).scalar() or 0
    receita = float(db.session.query(func.sum(Atendimento.total)).filter(
        *_filtro_periodo(inicio, fim, barbearia_id)).scalar() or 0)
    return jsonify({
        'periodo': {'inicio': inicio_str, 'fim': fim_str},
        'total_atendimentos': total,
        'receita_total': receita,
        'ticket_medio': round(receita / total, 2) if total else 0.0,
    })


@relatorios.get('/relatorios/por-barbeiro')
@admin_required
def por_barbeiro():
    barbearia_id = get_barbearia_atual()
    inicio_str = request.args.get('inicio', '').strip()
    fim_str    = request.args.get('fim', '').strip()
    if not inicio_str or not fim_str:
        return _erro('Parâmetros "inicio" e "fim" são obrigatórios.')
    try:
        inicio = datetime.strptime(inicio_str, '%Y-%m-%d')
        fim    = datetime.strptime(fim_str,    '%Y-%m-%d') + timedelta(days=1)
    except ValueError:
        return _erro('Formato inválido.')
    rows = (
        db.session.query(
            Barbeiro.id, Usuario.nome, Barbeiro.comissao_percentual,
            func.count(Atendimento.id), func.sum(Atendimento.total),
        )
        .join(Usuario, Barbeiro.usuario_id == Usuario.id)
        .join(Atendimento, Atendimento.barbeiro_id == Barbeiro.id)
        .filter(*_filtro_periodo(inicio, fim, barbearia_id))
        .group_by(Barbeiro.id, Usuario.nome, Barbeiro.comissao_percentual)
        .order_by(func.sum(Atendimento.total).desc()).all()
    )
    return jsonify([
        {'barbeiro_id': bid, 'barbeiro': nome,
         'total_atendimentos': int(t or 0), 'receita_gerada': float(r or 0),
         'comissao_calculada': round(float(r or 0) * float(c) / 100, 2)}
        for bid, nome, c, t, r in rows
    ])


@relatorios.get('/relatorios/produtos-mais-vendidos')
@admin_required
def produtos_mais_vendidos():
    barbearia_id = get_barbearia_atual()
    inicio_str = request.args.get('inicio', '').strip()
    fim_str    = request.args.get('fim', '').strip()
    if not inicio_str or not fim_str:
        return _erro('Parâmetros "inicio" e "fim" são obrigatórios.')
    try:
        inicio = datetime.strptime(inicio_str, '%Y-%m-%d')
        fim    = datetime.strptime(fim_str,    '%Y-%m-%d') + timedelta(days=1)
    except ValueError:
        return _erro('Formato inválido.')
    rows = (
        db.session.query(
            Produto.id, Produto.nome,
            func.sum(AtendimentoItem.quantidade),
            func.sum(AtendimentoItem.preco_unitario * AtendimentoItem.quantidade),
        )
        .join(AtendimentoItem, AtendimentoItem.produto_id == Produto.id)
        .join(Atendimento, Atendimento.id == AtendimentoItem.atendimento_id)
        .filter(AtendimentoItem.tipo == 'produto', *_filtro_periodo(inicio, fim, barbearia_id))
        .group_by(Produto.id, Produto.nome)
        .order_by(func.sum(AtendimentoItem.quantidade).desc()).all()
    )
    return jsonify([
        {'produto_id': pid, 'produto': n, 'quantidade_vendida': int(q or 0), 'receita': float(r or 0)}
        for pid, n, q, r in rows
    ])


@relatorios.get('/relatorios/clientes-frequentes')
@admin_required
def clientes_frequentes():
    barbearia_id = get_barbearia_atual()
    inicio_str = request.args.get('inicio', '').strip()
    fim_str    = request.args.get('fim', '').strip()
    if not inicio_str or not fim_str:
        return _erro('Parâmetros "inicio" e "fim" são obrigatórios.')
    try:
        inicio = datetime.strptime(inicio_str, '%Y-%m-%d')
        fim    = datetime.strptime(fim_str,    '%Y-%m-%d') + timedelta(days=1)
    except ValueError:
        return _erro('Formato inválido.')
    rows = (
        db.session.query(
            Cliente.id, Cliente.nome,
            func.count(Atendimento.id), func.sum(Atendimento.total),
        )
        .join(Atendimento, Atendimento.cliente_id == Cliente.id)
        .filter(*_filtro_periodo(inicio, fim, barbearia_id))
        .group_by(Cliente.id, Cliente.nome)
        .order_by(func.count(Atendimento.id).desc()).all()
    )
    return jsonify([
        {'cliente_id': cid, 'cliente': n, 'total_visitas': int(v or 0), 'total_gasto': float(g or 0)}
        for cid, n, v, g in rows
    ])


@relatorios.get('/relatorios/receita-diaria')
@admin_required
def receita_diaria():
    barbearia_id = get_barbearia_atual()
    inicio_str = request.args.get('inicio', '').strip()
    fim_str    = request.args.get('fim', '').strip()
    if not inicio_str or not fim_str:
        return _erro('Parâmetros "inicio" e "fim" são obrigatórios.')
    try:
        inicio = datetime.strptime(inicio_str, '%Y-%m-%d')
        fim    = datetime.strptime(fim_str,    '%Y-%m-%d') + timedelta(days=1)
    except ValueError:
        return _erro('Formato inválido.')
    rows = (
        db.session.query(cast(Atendimento.criado_em, Date), func.sum(Atendimento.total))
        .filter(*_filtro_periodo(inicio, fim, barbearia_id))
        .group_by(cast(Atendimento.criado_em, Date))
        .order_by(cast(Atendimento.criado_em, Date)).all()
    )
    return jsonify([{'data': str(d), 'receita': float(r or 0)} for d, r in rows])
