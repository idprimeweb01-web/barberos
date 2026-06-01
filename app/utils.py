import re
from flask_jwt_extended import get_jwt


def get_barbearia_atual():
    """Extrai barbearia_id do token JWT ativo (requer contexto de requisição)."""
    return get_jwt().get('barbearia_id')


def normalizar_telefone(tel):
    """Remove não-dígitos e valida 8–13 dígitos (suporta DDD + número brasileiro)."""
    digitos = re.sub(r'\D', '', tel or '')
    if len(digitos) < 8:
        return None, 'Telefone deve ter no mínimo 8 dígitos.'
    if len(digitos) > 13:
        return None, 'Telefone inválido — dígitos demais.'
    return digitos, None


# ── Helpers de perfil ──────────────────────────────────────────────────────────

def is_super_admin(usuario):
    return usuario is not None and usuario.perfil == 'super_admin'


def is_gestor(usuario):
    return usuario is not None and usuario.perfil == 'gestor'


def is_barbeiro(usuario):
    return usuario is not None and usuario.perfil == 'barbeiro'


def is_gestor_ou_super(usuario):
    return usuario is not None and usuario.perfil in ('gestor', 'super_admin')


def pode_gerenciar_barbearia(usuario, barbearia_id):
    """Super_admin pode gerenciar qualquer barbearia; gestor só a própria."""
    if usuario is None:
        return False
    if usuario.perfil == 'super_admin':
        return True
    if usuario.perfil == 'gestor':
        return usuario.barbearia_id == barbearia_id
    return False
