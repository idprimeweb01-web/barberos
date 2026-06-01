import re
from functools import wraps
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request,
)
from app import db
from app.models import Usuario, Barbeiro, Barbearia, SolicitacaoSenha

auth = Blueprint('auth', __name__, url_prefix='/auth')

PERFIS_VALIDOS = {'super_admin', 'gestor', 'barbeiro', 'cliente'}
_SLUG_RE = re.compile(r'^[a-z0-9-]+$')


def _erro(mensagem, codigo=400):
    return jsonify({'erro': mensagem}), codigo


# ── Decorators compartilhados (importados pelos outros blueprints) ─────────────

def super_admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        usuario = db.session.get(Usuario, int(get_jwt_identity()))
        if not usuario or usuario.perfil != 'super_admin':
            return _erro('Acesso restrito ao super administrador.', 403)
        return fn(*args, **kwargs)
    return wrapper


def gestor_required(fn):
    """Gestor OU super_admin."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        usuario = db.session.get(Usuario, int(get_jwt_identity()))
        if not usuario or usuario.perfil not in ('gestor', 'super_admin'):
            return _erro('Acesso restrito a gestores e administradores.', 403)
        return fn(*args, **kwargs)
    return wrapper


def barbeiro_required(fn):
    """Barbeiro, gestor OU super_admin."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        usuario = db.session.get(Usuario, int(get_jwt_identity()))
        if not usuario or usuario.perfil not in ('barbeiro', 'gestor', 'super_admin'):
            return _erro('Acesso restrito a barbeiros e gestores.', 403)
        return fn(*args, **kwargs)
    return wrapper


# Mantido por compatibilidade → alias de gestor_required
admin_required = gestor_required


# ── Helpers internos ───────────────────────────────────────────────────────────

def _hash_senha(senha: str) -> str:
    return generate_password_hash(senha)


def _verificar_senha(senha: str, hash_salvo: str) -> bool:
    return check_password_hash(hash_salvo, senha)


# ── POST /auth/barbearias ──────────────────────────────────────────────────────

@auth.post('/barbearias')
def criar_barbearia():
    """Cria uma nova barbearia. Rota aberta para o MVP."""
    dados = request.get_json(silent=True)
    if not dados:
        return _erro('Corpo da requisição inválido ou ausente.')

    nome = (dados.get('nome') or '').strip()
    slug = (dados.get('slug') or '').strip().lower()

    if not nome:
        return _erro('O campo "nome" é obrigatório.')
    if not slug:
        return _erro('O campo "slug" é obrigatório.')
    if not _SLUG_RE.match(slug):
        return _erro('O slug deve conter apenas letras minúsculas, números e hífens.')
    if len(slug) > 50:
        return _erro('O slug deve ter no máximo 50 caracteres.')

    if Barbearia.query.filter_by(slug=slug).first():
        return _erro('Este slug já está em uso.', 409)

    barbearia = Barbearia(nome=nome, slug=slug)
    db.session.add(barbearia)
    db.session.commit()

    return jsonify({
        'mensagem': 'Barbearia criada com sucesso.',
        'barbearia': {'id': barbearia.id, 'nome': barbearia.nome, 'slug': barbearia.slug},
    }), 201


# ── POST /auth/register ────────────────────────────────────────────────────────

@auth.post('/register')
def register():
    dados = request.get_json(silent=True)
    if not dados:
        return _erro('Corpo da requisição inválido ou ausente.')

    nome     = (dados.get('nome') or '').strip()
    telefone = (dados.get('telefone') or '').strip()
    email    = (dados.get('email') or '').strip().lower()
    senha    = (dados.get('senha') or '').strip()
    perfil   = (dados.get('perfil') or '').strip().lower()

    if not nome:
        return _erro('O campo "nome" é obrigatório.')
    if len(nome) > 100:
        return _erro('O campo "nome" deve ter no máximo 100 caracteres.')
    if not telefone:
        return _erro('O campo "telefone" é obrigatório.')
    if email and '@' not in email:
        return _erro('O campo "email" é inválido.')
    if not senha:
        return _erro('O campo "senha" é obrigatório.')
    if len(senha) < 6:
        return _erro('A senha deve ter no mínimo 6 caracteres.')
    if not perfil:
        return _erro('O campo "perfil" é obrigatório.')
    if perfil not in PERFIS_VALIDOS:
        return _erro(f'Perfil inválido. Use: {", ".join(sorted(PERFIS_VALIDOS))}.')

    barbearia_id = dados.get('barbearia_id')
    if not barbearia_id:
        slug = (dados.get('barbearia_slug') or '').strip().lower()
        if not slug:
            return _erro('Informe "barbearia_id" ou "barbearia_slug".')
        barbearia = Barbearia.query.filter_by(slug=slug, ativo=True).first()
        if not barbearia:
            return _erro('Barbearia não encontrada.', 404)
        barbearia_id = barbearia.id
    else:
        if not db.session.get(Barbearia, barbearia_id):
            return _erro('Barbearia não encontrada.', 404)

    if email and Usuario.query.filter_by(email=email).first():
        return _erro('E-mail já cadastrado.', 409)

    usuario = Usuario(
        barbearia_id=barbearia_id,
        nome=nome,
        telefone=telefone,
        email=email or None,
        senha=_hash_senha(senha),
        perfil=perfil,
    )
    db.session.add(usuario)
    db.session.flush()

    if perfil == 'barbeiro':
        db.session.add(Barbeiro(
            barbearia_id=barbearia_id,
            usuario_id=usuario.id,
            comissao_percentual=0,
        ))

    db.session.commit()

    return jsonify({
        'mensagem': 'Usuário cadastrado com sucesso.',
        'usuario': {
            'id':           usuario.id,
            'nome':         usuario.nome,
            'telefone':     usuario.telefone,
            'email':        usuario.email,
            'perfil':       usuario.perfil,
            'barbearia_id': usuario.barbearia_id,
        },
    }), 201


# ── POST /auth/login ───────────────────────────────────────────────────────────

@auth.post('/login')
def login():
    dados = request.get_json(silent=True)
    if not dados:
        return _erro('Corpo da requisição inválido ou ausente.')

    email = (dados.get('email') or '').strip().lower()
    senha = (dados.get('senha') or '').strip()

    if not email:
        return _erro('O campo "email" é obrigatório.')
    if not senha:
        return _erro('O campo "senha" é obrigatório.')

    usuario = Usuario.query.filter_by(email=email).first()
    if not usuario or not usuario.senha:
        return _erro('E-mail ou senha inválidos.', 401)
    if not _verificar_senha(senha, usuario.senha):
        return _erro('E-mail ou senha inválidos.', 401)
    if not usuario.ativo:
        return _erro('Usuário inativo. Entre em contato com o administrador.', 403)

    token = create_access_token(
        identity=str(usuario.id),
        additional_claims={'barbearia_id': usuario.barbearia_id},
    )

    return jsonify({
        'mensagem':   'Login realizado com sucesso.',
        'token':      token,
        'usuario': {
            'id':           usuario.id,
            'nome':         usuario.nome,
            'email':        usuario.email,
            'perfil':       usuario.perfil,
            'barbearia_id': usuario.barbearia_id,
        },
    }), 200


# ── PUT /auth/alterar-senha ───────────────────────────────────────────────────

@auth.put('/alterar-senha')
@jwt_required()
def alterar_senha():
    uid     = int(get_jwt_identity())
    usuario = db.session.get(Usuario, uid)
    if not usuario:
        return _erro('Usuário não encontrado.', 404)
    dados       = request.get_json(silent=True) or {}
    senha_atual = (dados.get('senha_atual') or '').strip()
    nova_senha  = (dados.get('nova_senha')  or '').strip()
    if not senha_atual: return _erro('"senha_atual" é obrigatório.')
    if not nova_senha:  return _erro('"nova_senha" é obrigatório.')
    if len(nova_senha) < 6: return _erro('Nova senha mínimo 6 caracteres.')
    if not _verificar_senha(senha_atual, usuario.senha):
        return _erro('Senha atual incorreta.', 401)
    usuario.senha = _hash_senha(nova_senha)
    db.session.commit()
    return jsonify({'mensagem': 'Senha alterada com sucesso.'})


# ── GET /auth/me ───────────────────────────────────────────────────────────────

@auth.get('/me')
@jwt_required()
def me():
    usuario = db.session.get(Usuario, int(get_jwt_identity()))
    if not usuario:
        return _erro('Usuário não encontrado.', 404)
    if not usuario.ativo:
        return _erro('Usuário inativo.', 403)

    return jsonify({
        'id':           usuario.id,
        'nome':         usuario.nome,
        'telefone':     usuario.telefone,
        'email':        usuario.email,
        'perfil':       usuario.perfil,
        'barbearia_id': usuario.barbearia_id,
        'ativo':        usuario.ativo,
        'criado_em':    usuario.criado_em.isoformat() if usuario.criado_em else None,
    }), 200


# ── PUT /auth/admin/barbeiros/<id>/comissao ────────────────────────────────────

@auth.put('/admin/barbeiros/<int:barbeiro_id>/comissao')
@gestor_required
def atualizar_comissao(barbeiro_id):
    from app.utils import get_barbearia_atual
    barbearia_id = get_barbearia_atual()

    dados = request.get_json(silent=True)
    if not dados or 'comissao_percentual' not in dados:
        return _erro('O campo "comissao_percentual" é obrigatório.')

    comissao = dados['comissao_percentual']
    if not isinstance(comissao, (int, float)) or comissao < 0 or comissao > 100:
        return _erro('"comissao_percentual" deve ser um número entre 0 e 100.')

    barbeiro = Barbeiro.query.filter_by(id=barbeiro_id, barbearia_id=barbearia_id).first()
    if not barbeiro:
        return _erro('Barbeiro não encontrado.', 404)

    barbeiro.comissao_percentual = comissao
    db.session.commit()

    usuario = db.session.get(Usuario, barbeiro.usuario_id)
    return jsonify({
        'mensagem': 'Comissão atualizada com sucesso.',
        'barbeiro': {
            'id':                  barbeiro.id,
            'nome':                usuario.nome if usuario else None,
            'comissao_percentual': float(barbeiro.comissao_percentual),
        },
    })


# ── POST /auth/esqueci-senha ───────────────────────────────────────────────────

@auth.post('/esqueci-senha')
def esqueci_senha():
    """Rota pública. Cria solicitação de redefinição sem revelar se email existe."""
    dados = request.get_json(silent=True)
    email = (dados.get('email') or '').strip().lower() if dados else ''

    if not email:
        return _erro('O campo "email" é obrigatório.')

    usuario = Usuario.query.filter_by(email=email, ativo=True).first()
    if usuario and usuario.barbearia_id:
        # Evita solicitações duplicadas pendentes para o mesmo usuário
        existente = SolicitacaoSenha.query.filter_by(
            usuario_id=usuario.id, status='pendente'
        ).first()
        if not existente:
            db.session.add(SolicitacaoSenha(
                usuario_id=usuario.id,
                barbearia_id=usuario.barbearia_id,
            ))
            db.session.commit()

    return jsonify({
        'mensagem': 'Se o e-mail existir, o administrador será notificado.'
    }), 200


# ── GET /gestor/solicitacoes-senha ─────────────────────────────────────────────

@auth.get('/gestor/solicitacoes-senha')
@gestor_required
def listar_solicitacoes():
    from app.utils import get_barbearia_atual
    barbearia_id = get_barbearia_atual()

    status_filtro = request.args.get('status', 'pendente')
    if status_filtro not in ('pendente', 'resolvido'):
        status_filtro = 'pendente'

    rows = (
        db.session.query(SolicitacaoSenha, Usuario)
        .join(Usuario, SolicitacaoSenha.usuario_id == Usuario.id)
        .filter(
            SolicitacaoSenha.barbearia_id == barbearia_id,
            SolicitacaoSenha.status       == status_filtro,
        )
        .order_by(SolicitacaoSenha.criado_em.desc())
        .all()
    )

    return jsonify([
        {
            'id':         sol.id,
            'nome':       u.nome,
            'email':      u.email,
            'telefone':   u.telefone,
            'criado_em':  sol.criado_em.isoformat() if sol.criado_em else None,
        }
        for sol, u in rows
    ])


# ── PUT /gestor/solicitacoes-senha/<id>/resolver ───────────────────────────────

@auth.put('/gestor/solicitacoes-senha/<int:solicitacao_id>/resolver')
@gestor_required
def resolver_solicitacao(solicitacao_id):
    from app.utils import get_barbearia_atual
    barbearia_id = get_barbearia_atual()

    sol = SolicitacaoSenha.query.filter_by(
        id=solicitacao_id, barbearia_id=barbearia_id
    ).first()
    if not sol:
        return _erro('Solicitação não encontrada.', 404)
    if sol.status == 'resolvido':
        return _erro('Esta solicitação já foi resolvida.')

    dados = request.get_json(silent=True)
    nova_senha = (dados.get('nova_senha') or '').strip() if dados else ''
    if not nova_senha:
        return _erro('O campo "nova_senha" é obrigatório.')
    if len(nova_senha) < 6:
        return _erro('A nova senha deve ter no mínimo 6 caracteres.')

    usuario = db.session.get(Usuario, sol.usuario_id)
    if not usuario:
        return _erro('Usuário não encontrado.', 404)

    usuario.senha = _hash_senha(nova_senha)
    sol.status = 'resolvido'
    db.session.commit()

    return jsonify({
        'mensagem':  'Senha redefinida com sucesso.',
        'usuario': {
            'nome':     usuario.nome,
            'telefone': usuario.telefone,
            'email':    usuario.email,
        },
    })
