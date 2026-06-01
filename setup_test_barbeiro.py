from datetime import datetime, date, timedelta, time as Time
from app import create_app, db
from app.models import (
    Barbearia, Usuario, Barbeiro, Cliente, Servico, BarbeiroServico,
    ConfiguracaoAgenda, Agendamento,
)

app = create_app()
with app.app_context():
    # Encontra o barbeiro@barbearia.com
    u = Usuario.query.filter_by(email='barbeiro@barbearia.com').first()
    barb = Barbeiro.query.filter_by(usuario_id=u.id, barbearia_id=1).first()
    print(f"Barbeiro: {u.nome}, barbeiro_id={barb.id}")

    # Garante ConfiguracaoAgenda
    cfg = ConfiguracaoAgenda.query.filter_by(barbeiro_id=barb.id, barbearia_id=1).first()
    if not cfg:
        cfg = ConfiguracaoAgenda(
            barbeiro_id=barb.id, barbearia_id=1,
            horario_abertura=Time(8,0), horario_fechamento=Time(18,0),
            intervalo_minutos=60, loja_aberta=True,
        )
        db.session.add(cfg)
        db.session.commit()
        print("Config agenda criada")
    else:
        print("Config agenda ja existe")

    # Pega um servico da barbearia
    sv = Servico.query.filter_by(barbearia_id=1, ativo=True).first()
    # Vincula se necessario
    if not BarbeiroServico.query.filter_by(barbeiro_id=barb.id, servico_id=sv.id).first():
        db.session.add(BarbeiroServico(barbeiro_id=barb.id, servico_id=sv.id))
        db.session.commit()
        print(f"Servico '{sv.nome}' vinculado")

    # Cria ou encontra cliente de teste
    cli = Cliente.query.filter_by(telefone='11987654321', barbearia_id=1).first()
    if not cli:
        cli = Cliente(nome='Carlos Teste', telefone='87654321', barbearia_id=1)
        db.session.add(cli)
        db.session.flush()
        print("Cliente criado")
    else:
        print(f"Cliente existente: {cli.nome}")

    # Cria agendamento para HOJE
    hoje = date.today()
    hora_ag = datetime.combine(hoje, Time(9, 0))
    ag_existe = Agendamento.query.filter_by(
        barbeiro_id=barb.id, barbearia_id=1, cliente_id=cli.id,
        status='agendado'
    ).filter(Agendamento.data_hora >= datetime.combine(hoje, Time(0,0))).first()

    if not ag_existe:
        ag = Agendamento(
            barbearia_id=1, cliente_id=cli.id, barbeiro_id=barb.id,
            servico_id=sv.id, data_hora=hora_ag,
            duracao_minutos=sv.duracao_minutos, status='agendado',
        )
        db.session.add(ag)
        db.session.commit()
        print(f"Agendamento criado para hoje 09:00 (id={ag.id})")
    else:
        print(f"Agendamento ja existe (id={ag_existe.id})")
