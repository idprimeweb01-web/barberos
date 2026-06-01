#!/usr/bin/env python3
"""
Limpa o banco e cria super admin inicial.

Uso:
  python limpar_banco.py

Credenciais criadas:
  Email : adm@barbearia.com
  Senha : 123456
  Perfil: super_admin
"""

import sys
from app import create_app, db
from app.models import (
    Barbearia, Usuario, Barbeiro, BarbeiroServico, Servico,
    ConfiguracaoAgenda, Agendamento, AgendamentoServico, HorarioBloqueado,
    Produto, ReservaProduto, Atendimento, AtendimentoItem,
    Pagamento, Cliente, SolicitacaoSenha, SolicitacaoLiberacao,
)
from werkzeug.security import generate_password_hash

TABELAS_ORDEM = [
    Pagamento,
    AtendimentoItem,
    ReservaProduto,
    AgendamentoServico,
    Atendimento,
    Agendamento,
    HorarioBloqueado,
    SolicitacaoLiberacao,
    SolicitacaoSenha,
    BarbeiroServico,
    ConfiguracaoAgenda,
    Barbeiro,
    Servico,
    Produto,
    Cliente,
    Usuario,
    Barbearia,
]

SUPER_EMAIL = "adm@barbearia.com"
SUPER_SENHA = "123456"
SUPER_NOME  = "Super Admin"
SUPER_TEL   = "11999999999"


def limpar_tudo(session):
    print("Deletando dados...")
    for modelo in TABELAS_ORDEM:
        n = session.query(modelo).delete(synchronize_session=False)
        if n:
            print(f"  {modelo.__tablename__}: {n} registro(s) removido(s)")
    session.commit()
    print("Banco zerado.")


def criar_super_admin(session):
    if Usuario.query.filter_by(email=SUPER_EMAIL).first():
        print(f"Super admin já existe: {SUPER_EMAIL}")
        return

    u = Usuario(
        nome=SUPER_NOME,
        telefone=SUPER_TEL,
        email=SUPER_EMAIL,
        senha=generate_password_hash(SUPER_SENHA),
        perfil="super_admin",
        barbearia_id=None,
        ativo=True,
    )
    session.add(u)
    session.commit()
    print(f"Super admin criado: {SUPER_EMAIL} / {SUPER_SENHA}")


def main():
    app = create_app()
    with app.app_context():
        resposta = input(
            "\n⚠️  Isso apaga TODOS os dados do banco.\n"
            "   Digite 'sim' para confirmar: "
        ).strip().lower()

        if resposta != "sim":
            print("Operação cancelada.")
            sys.exit(0)

        limpar_tudo(db.session)
        criar_super_admin(db.session)

        print("\n✅  Pronto!")
        print(f"   Email : {SUPER_EMAIL}")
        print(f"   Senha : {SUPER_SENHA}")
        print(f"   Perfil: super_admin\n")


if __name__ == "__main__":
    main()
