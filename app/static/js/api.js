const BASE_URL = window.location.origin;

const api = (() => {
  const TOKEN_KEY = 'barberos_token';
  const USER_KEY  = 'barberos_user';

  function setToken(token) { localStorage.setItem(TOKEN_KEY, token); }
  function getToken()      { return localStorage.getItem(TOKEN_KEY); }
  function setUser(user)   { localStorage.setItem(USER_KEY, JSON.stringify(user)); }
  function getUser()       { try { return JSON.parse(localStorage.getItem(USER_KEY)); } catch { return null; } }
  function getPerfil()     { const u = getUser(); return u ? u.perfil : null; }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    window.location.href = '/login';
  }

  function _headers(extra = {}) {
    const h = { 'Content-Type': 'application/json', ...extra };
    const t = getToken();
    if (t) h['Authorization'] = `Bearer ${t}`;
    return h;
  }

  async function _tratar(res) {
    if (res.status === 401 && window.location.pathname !== '/login') {
      logout();
      throw new Error('Sessão expirada. Faça login novamente.');
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.erro || data.msg || `Erro ${res.status}`);
    return data;
  }

  async function get(rota) {
    const res = await fetch(`${BASE_URL}${rota}`, { method: 'GET', headers: _headers() });
    return _tratar(res);
  }
  async function post(rota, dados = {}) {
    const res = await fetch(`${BASE_URL}${rota}`, { method: 'POST', headers: _headers(), body: JSON.stringify(dados) });
    return _tratar(res);
  }
  async function put(rota, dados = {}) {
    const res = await fetch(`${BASE_URL}${rota}`, { method: 'PUT', headers: _headers(), body: JSON.stringify(dados) });
    return _tratar(res);
  }
  async function del(rota) {
    const res = await fetch(`${BASE_URL}${rota}`, { method: 'DELETE', headers: _headers() });
    return _tratar(res);
  }

  async function _uploadFoto(rota, arquivo) {
    const form = new FormData();
    form.append('arquivo', arquivo);
    const res = await fetch(`${BASE_URL}${rota}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${getToken()}` },
      body: form,
    });
    return _tratar(res);
  }

  // ── Namespaces ──────────────────────────────────────────────────────────────

  const barbeiros = {
    listar:  ()        => get('/admin/barbeiros'),
    criar:   (d)       => post('/admin/barbeiros', d),
    editar:  (id, d)   => put(`/admin/barbeiros/${id}`, d),
    deletar: (id)      => del(`/admin/barbeiros/${id}`),
  };

  const servicos = {
    listar:  ()        => get('/servicos'),
    criar:   (d)       => post('/servicos', d),
    editar:  (id, d)   => put(`/servicos/${id}`, d),
    deletar: (id)      => del(`/servicos/${id}`),
  };

  const produtos = {
    listar:  ()        => get('/admin/produtos'),
    criar:   (d)       => post('/admin/produtos', d),
    editar:  (id, d)   => put(`/admin/produtos/${id}`, d),
    deletar: (id)      => del(`/admin/produtos/${id}`),
  };

  const agenda = {
    listar:               ()          => get('/admin/agenda'),
    atualizar:            (id, d)     => put(`/admin/agenda/${id}`, d),
    bloquear:             (id, d)     => post(`/admin/agenda/${id}/bloquear`, d),
    grade:                (bid, data) => get(`/admin/agenda/grade?barbeiro_id=${bid}&data=${data}`),
    agendarManual:        (d)         => post('/admin/agenda/agendamento-manual', d),
    cancelar:             (id)        => del(`/admin/agendamentos/${id}`),
    bloqueiosMes:         (mes, ano)  => get(`/admin/agenda/bloqueios/mes?mes=${mes}&ano=${ano}`),
    horarios:             (data)      => get(`/admin/agenda/horarios?data=${data}`),
    bloqueiosCriar:       (d)         => post('/admin/agenda/bloqueios', d),
    bloqueiosRemover:     (id)        => del(`/admin/agenda/bloqueios/${id}`),
    solicitacoesLib:      (status)    => get(`/admin/agenda/solicitacoes-liberacao?status=${status || 'pendente'}`),
    responderLiberacao:   (id, d)     => put(`/admin/agenda/solicitacoes-liberacao/${id}`, d),
  };

  const senha = {
    listar:   (status = 'pendente') => get(`/auth/gestor/solicitacoes-senha?status=${status}`),
    resolver: (id, nova_senha)      => put(`/auth/gestor/solicitacoes-senha/${id}/resolver`, { nova_senha }),
  };

  const metricas = () => get('/admin/metricas');

  // ── Super Admin ─────────────────────────────────────────────
  const superApi = {
    dashboard:  () => get('/super/dashboard/metricas'),
    barbearias: {
      listar: ()       => get('/super/barbearias/lista'),
      criar:  (d)      => post('/super/barbearias', d),
      editar: (id, d)  => put(`/super/barbearias/${id}`, d),
    },
    gestores: {
      listar:       ()       => get('/super/gestores/lista'),
      criar:        (d)      => post('/super/gestor', d),
      editar:       (id, d)  => put(`/super/gestor/${id}`, d),
      resetarSenha: (id, d)  => put(`/super/gestor/${id}/resetar-senha`, d),
    },
  };

  // ── Público (sem JWT) ───────────────────────────────────────
  const _pub = {
    get:  async (rota) => {
      const res = await fetch(`${BASE_URL}${rota}`);
      if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.erro || `Erro ${res.status}`); }
      return res.json();
    },
    post: async (rota, dados) => {
      const res = await fetch(`${BASE_URL}${rota}`, {
        method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(dados),
      });
      if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.erro || `Erro ${res.status}`); }
      return res.json();
    },
  };

  const publico = {
    info:        (slug)            => _pub.get(`/b/${slug}/barbearia-info`),
    barbeiros:   (slug)            => _pub.get(`/b/${slug}/barbeiros`),
    servicos:    (slug)            => _pub.get(`/b/${slug}/servicos`),
    svBarbeiro:  (slug, bid)       => _pub.get(`/b/${slug}/barbeiros/${bid}/servicos`),
    horarios:    (slug, bid, data) => _pub.get(`/b/${slug}/agenda/horarios-disponiveis?barbeiro_id=${bid}&data=${data}`),
    agendar:     (slug, dados)     => _pub.post(`/b/${slug}/agendamentos`, dados),
    agendamento: (slug, id)        => _pub.get(`/b/${slug}/agendamento/${id}`),
  };

  // ── Barbeiro (painel do barbeiro) ───────────────────────────
  const barbeiro = {
    agenda:        (data)       => get(`/agenda/meus-agendamentos?data=${data}`),
    iniciar:       (id)         => post(`/agendamentos/${id}/iniciar`, {}),
    caixa:         (id)         => get(`/caixa/agendamento/${id}`),
    produtos:      ()           => get('/produtos'),
    addItem:       (at, dados)  => post(`/atendimentos/${at}/itens`, dados),
    delItem:       (at, item)   => del(`/atendimentos/${at}/itens/${item}`),
    efetuar:       (at, forma)  => put(`/atendimentos/${at}/efetuar`, { forma_pagamento: forma }),
    minhaConfig:           ()    => get('/agenda/minha-config'),
    urlAgendamento:        ()    => get('/agenda/url-agendamento'),
    meusServicos:          ()    => get('/agenda/meus-servicos'),
    agendarManual:         (d)   => post('/agenda/agendamento-manual', d),
    cancelar:              (id)  => del(`/agendamentos/${id}`),
    dashboard:             ()    => get('/agenda/meu-dashboard'),
    perfil:                ()    => get('/agenda/meu-perfil'),
    atualizarPerfil:       (d)   => put('/agenda/meu-perfil', d),
    alterarSenha:          (d)   => put('/auth/alterar-senha', d),
    esqueceuSenha:         (email) => post('/auth/esqueci-senha', { email }),
    solicitarLiberacao:    (d)   => post('/agenda/solicitar-liberacao', d),
    notificacoesLiberacao: ()    => get('/agenda/notificacoes-liberacao'),
  };

  const upload = {
    barbearia: (id, arq) => _uploadFoto(`/upload/barbearia/${id}/logo`, arq),
    barbeiro:  (id, arq) => _uploadFoto(`/upload/barbeiro/${id}/foto`,  arq),
    servico:   (id, arq) => _uploadFoto(`/upload/servico/${id}/foto`,   arq),
    produto:   (id, arq) => _uploadFoto(`/upload/produto/${id}/foto`,   arq),
    cliente:   (id, arq) => _uploadFoto(`/upload/cliente/${id}/foto`,   arq),
  };

  const barbearia = {
    status:    ()        => get('/admin/barbearia/status'),
    setStatus: (aberta)  => put('/admin/barbearia/status', { aberta }),
    tema:      ()        => get('/admin/barbearia/tema'),
  };

  const clientes = {
    listar:       (q)      => get(`/clientes${q ? '?q=' + encodeURIComponent(q) : ''}`),
    perfil:       (id)     => get(`/clientes/${id}/perfil`),
    criar:        (d)      => post('/clientes', d),
    editar:       (id, d)  => put(`/clientes/${id}`, d),
    deletar:      (id)     => del(`/clientes/${id}`),
    listarAdmin:  (opts = {}) => {
      const p = new URLSearchParams();
      if (opts.q)           p.set('q',           opts.q);
      if (opts.status)      p.set('status',       opts.status);
      if (opts.barbeiro_id) p.set('barbeiro_id',  opts.barbeiro_id);
      const s = p.toString();
      return get(`/admin/clientes${s ? '?' + s : ''}`);
    },
  };

  return {
    get, post, put, delete: del,
    setToken, getToken, setUser, getUser, getPerfil, logout,
    barbeiros, servicos, produtos, agenda, senha, metricas, upload, barbeiro,
    barbearia, clientes,
    super: superApi, publico,
  };
})();
