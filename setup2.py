from datetime import datetime, date, timedelta, time as Time
from app import create_app, db
from app.models import (
    Barbearia, Usuario, Barbeiro, Cliente, Servico, BarbeiroServico,
    ConfiguracaoAgenda, Agendamento,
)

app = create_app()
with app.app_context():
    u = Usuario.query.filter_by(email='barbeiro@barbearia.com').first()
    print(f"Usuario: {u.id} {u.nome} perfil={u.perfil} barb_id={u.barbearia_id}")
    
    # Busca barbeiro por usuario_id (sem filtro de barbearia pois pode ser outra)
    barbs = Barbeiro.query.filter_by(usuario_id=u.id).all()
    print(f"Barbeiros encontrados: {[(b.id, b.barbearia_id) for b in barbs]}")
    
    # Usa o primeiro ativo
    barb = Barbeiro.query.filter_by(usuario_id=u.id, ativo=True).first()
    if not barb:
        # Cria na barbearia 1
        barb = Barbeiro(barbearia_id=1, usuario_id=u.id, comissao_percentual=40)
        db.session.add(barb)
        db.session.commit()
        print(f"Barbeiro criado: {barb.id}")
    
    barbearia_id = barb.barbearia_id
    print(f"Usando: barbeiro_id={barb.id} barbearia_id={barbearia_id}")

    # Garante ConfiguracaoAgenda
    cfg = ConfiguracaoAgenda.query.filter_by(barbeiro_id=barb.id, barbearia_id=barbearia_id).first()
    if not cfg:
        cfg = ConfiguracaoAgenda(
            barbeiro_id=barb.id, barbearia_id=barbearia_id,
            horario_abertura=Time(8,0), horario_fechamento=Time(18,0),
            intervalo_minutos=60, loja_aberta=True,
        )
        db.session.add(cfg)
        db.session.commit()
        print("Config agenda criada")

    # Pega servico
    sv = Servico.query.filter_by(barbearia_id=barbearia_id, ativo=True).first()
    print(f"Servico: {sv.id} {sv.nome}")

    if not BarbeiroServico.query.filter_by(barbeiro_id=barb.id, servico_id=sv.id).first():
        db.session.add(BarbeiroServico(barbeiro_id=barb.id, servico_id=sv.id))
        db.session.commit()

    # Cria cliente
    cli = Cliente.query.filter_by(telefone='87654321', barbearia_id=barbearia_id).first()
    if not cli:
        cli = Cliente(nome='Carlos Teste', telefone='87654321', barbearia_id=barbearia_id)
        db.session.add(cli)
        db.session.flush()
        print("Cliente criado")

    # Cria agendamento hoje
    hoje = date.today()
    hora_ag = datetime.combine(hoje, Time(9, 0))
    ag = Agendamento.query.filter(
        Agendamento.barbeiro_id == barb.id,
        Agendamento.status == 'agendado',
        Agendamento.data_hora >= datetime.combine(hoje, Time(0,0)),
        Agendamento.data_hora < datetime.combine(hoje, Time(23,59)),
    ).first()

    if not ag:
        ag = Agendamento(
            barbearia_id=barbearia_id, cliente_id=cli.id, barbeiro_id=barb.id,
            servico_id=sv.id, data_hora=hora_ag,
            duracao_minutos=sv.duracao_minutos, status='agendado',
        )
        db.session.add(ag)
        db.session.commit()
        print(f"Agendamento criado: id={ag.id} data={hora_ag}")
    else:
        print(f"Agendamento ja existe: id={ag.id}")
    
    print("DONE")
