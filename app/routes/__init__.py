from flask import Blueprint, redirect, url_for, render_template

main = Blueprint('main', __name__)


@main.get('/')
def index():
    return redirect(url_for('main.login'))


@main.get('/login')
def login():
    return render_template('auth/login.html')


# ── Painel Barbeiro ────────────────────────────────────────────────────────────

@main.get('/barbeiro/dashboard')
def barbeiro_dashboard():
    return render_template('barbeiro/dashboard.html')

@main.get('/barbeiro/agenda')
def barbeiro_agenda():
    return render_template('barbeiro/agenda.html')

@main.get('/barbeiro/produtos')
def barbeiro_produtos():
    return render_template('barbeiro/produtos.html')

@main.get('/barbeiro/perfil')
def barbeiro_perfil():
    return render_template('barbeiro/perfil.html')

@main.get('/barbeiro/clientes')
def barbeiro_clientes():
    return render_template('barbeiro/clientes.html')


@main.get('/barbeiro/redefinicoes')
def barbeiro_redefinicoes():
    return render_template('barbeiro/redefinicoes.html')

@main.get('/barbeiro/configuracoes')
def barbeiro_configuracoes():
    return render_template('barbeiro/configuracoes.html')

@main.get('/barbeiro/caixa/<int:agendamento_id>')
def barbeiro_caixa(agendamento_id):
    return render_template('barbeiro/caixa.html', agendamento_id=agendamento_id)


# ── Painel Admin (legado) ──────────────────────────────────────────────────────

@main.get('/admin/dashboard')
def admin_dashboard():
    return render_template('admin/dashboard.html')


# ── Painel Gestor ──────────────────────────────────────────────────────────────

@main.get('/gestor/dashboard')
def gestor_dashboard():
    return render_template('gestor/dashboard.html')


@main.get('/gestor/barbeiros')
def gestor_barbeiros():
    return render_template('gestor/barbeiros.html')


@main.get('/gestor/servicos')
def gestor_servicos():
    return render_template('gestor/servicos.html')


@main.get('/gestor/produtos')
def gestor_produtos():
    return render_template('gestor/produtos.html')


@main.get('/gestor/agenda')
def gestor_agenda():
    return render_template('gestor/agenda.html')


@main.get('/gestor/clientes')
def gestor_clientes():
    return render_template('gestor/clientes.html')


@main.get('/gestor/esqueci-senha')
def gestor_esqueci_senha():
    return render_template('gestor/esqueci_senha.html')


@main.get('/gestor/relatorios')
def gestor_relatorios():
    return render_template('gestor/relatorios.html')


# ── Painel Super Admin ─────────────────────────────────────────────────────────

@main.get('/super/dashboard')
def super_dashboard():
    return render_template('super/dashboard.html')


@main.get('/super/barbearias')
def super_barbearias():
    return render_template('super/barbearias.html')


@main.get('/super/gestores')
def super_gestores():
    return render_template('super/gestores.html')


@main.get('/super/relatorios')
def super_relatorios():
    return render_template('super/relatorios.html')


# ── Público (cliente final) ────────────────────────────────────────────────────

@main.get('/b/<slug>/')
def public_index(slug):
    return render_template('public/index.html', slug=slug)


@main.get('/b/<slug>/agendar')
def public_agendar(slug):
    return render_template('public/agendar.html', slug=slug)


@main.get('/b/<slug>/confirmacao/<int:ag_id>')
def public_confirmacao(slug, ag_id):
    return render_template('public/confirmacao.html', slug=slug, ag_id=ag_id)
