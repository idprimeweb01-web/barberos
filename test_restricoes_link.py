"""
Testa:
 1. Restrição de produtos: barbeiro → 403 em POST/PUT/DELETE /admin/produtos
 2. Gestor ainda pode CRUD via /admin/produtos
 3. url_agendamento: coluna existe, GET /agenda/url-agendamento retorna URL
 4. Super admin edita url_agendamento via PUT /super/barbearias/<id>
 5. Gestor e barbeiro veem URL atualizada
 6. Rotas HTML têm o banner de booking
"""
import sys, time, requests
if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')

BASE = 'http://127.0.0.1:5000'
TS   = str(int(time.time()))[-6:]

def h(t=None):
    d = {'Content-Type':'application/json'}
    if t: d['Authorization'] = f'Bearer {t}'
    return d

ok_c = fail_c = 0
def check(desc, passed, detail=''):
    global ok_c, fail_c
    print(f'  [{" OK   " if passed else "FALHOU"}] {desc}')
    if detail: print(f'           -> {detail}')
    if passed: ok_c += 1
    else: fail_c += 1

print(f'\n{"="*62}')
print('  TESTE RESTRIÇÃO PRODUTOS + LINK AGENDAMENTO')
print(f'{"="*62}\n')

# ── Setup ─────────────────────────────────────────────────────
r = requests.post(f'{BASE}/auth/login', headers=h(),
    json={'email':'adm@barbearia.com','senha':'senha123'}, timeout=10)
sa = r.json().get('token')
check('Login super admin', r.status_code == 200)

slug = f'restrict{TS}'
r = requests.post(f'{BASE}/super/barbearias', headers=h(sa),
    json={'nome':'Restrict Test','slug':slug}, timeout=10)
bid = r.json().get('barbearia',{}).get('id')
check('Criar barbearia', r.status_code == 201 and bool(bid), f'id={bid}')

r = requests.post(f'{BASE}/super/gestor', headers=h(sa),
    json={'nome':'Gestor R','email':f'gr{TS}@t.com','telefone':'11900000050',
          'senha':'senha123','barbearia_id':bid}, timeout=10)
check('Criar gestor', r.status_code == 201)

r = requests.post(f'{BASE}/auth/login', headers=h(),
    json={'email':f'gr{TS}@t.com','senha':'senha123'}, timeout=10)
gt = r.json().get('token')
check('Login gestor', r.status_code == 200 and bool(gt))

r = requests.post(f'{BASE}/admin/barbeiros', headers=h(gt),
    json={'nome':'Barb R','email':f'br{TS}@t.com','telefone':'11900000049',
          'senha':'senha123','comissao_percentual':0,'servicos_ids':[]}, timeout=10)
check('Criar barbeiro', r.status_code == 201)

r = requests.post(f'{BASE}/auth/login', headers=h(),
    json={'email':f'br{TS}@t.com','senha':'senha123'}, timeout=10)
bt = r.json().get('token')
check('Login barbeiro', r.status_code == 200 and bool(bt))

print('\n  1. Restrição de acesso a produtos:')

# Barbeiro: GET /admin/produtos → 200 (pode VER)
r = requests.get(f'{BASE}/admin/produtos', headers=h(bt), timeout=10)
check('Barbeiro GET /admin/produtos → 200 (pode VER)', r.status_code == 200)

# Barbeiro: POST /admin/produtos → 403 (NÃO pode criar)
r = requests.post(f'{BASE}/admin/produtos', headers=h(bt),
    json={'nome':'X','preco':10,'quantidade_estoque':1}, timeout=10)
check('Barbeiro POST /admin/produtos → 403 (não pode criar)',
      r.status_code == 403, f"status={r.status_code} erro={r.json().get('erro','')[:40]}")

# Barbeiro: PUT /admin/produtos/1 → 403
r = requests.put(f'{BASE}/admin/produtos/1', headers=h(bt),
    json={'nome':'Y'}, timeout=10)
check('Barbeiro PUT /admin/produtos/<id> → 403', r.status_code == 403)

# Barbeiro: DELETE /admin/produtos/1 → 403
r = requests.delete(f'{BASE}/admin/produtos/1', headers=h(bt), timeout=10)
check('Barbeiro DELETE /admin/produtos/<id> → 403', r.status_code == 403)

# Gestor: ainda pode CRUD
r = requests.post(f'{BASE}/admin/produtos', headers=h(gt),
    json={'nome':'Produto Gestor','preco':25,'quantidade_estoque':5}, timeout=10)
pid = r.json().get('produto',{}).get('id')
check('Gestor POST /admin/produtos → 201', r.status_code == 201 and bool(pid))

r = requests.put(f'{BASE}/admin/produtos/{pid}', headers=h(gt),
    json={'preco':30}, timeout=10)
check('Gestor PUT /admin/produtos/<id> → 200', r.status_code == 200)

r = requests.delete(f'{BASE}/admin/produtos/{pid}', headers=h(gt), timeout=10)
check('Gestor DELETE /admin/produtos/<id> → 200', r.status_code == 200)

print('\n  2. URL de agendamento:')

# GET /agenda/url-agendamento (barbeiro) → URL padrão /b/{slug}/
r = requests.get(f'{BASE}/agenda/url-agendamento', headers=h(bt), timeout=10)
d = r.json() if r.ok else {}
check('Barbeiro GET /agenda/url-agendamento → 200',
      r.status_code == 200 and 'url' in d,
      f"url={d.get('url')} slug={d.get('slug')}")
check('URL padrão é /b/{slug}/',
      d.get('url') == f'/b/{slug}/', f"url={d.get('url')} esperado=/b/{slug}/")

# GET /agenda/url-agendamento (gestor) → também funciona
r = requests.get(f'{BASE}/agenda/url-agendamento', headers=h(gt), timeout=10)
d_g = r.json() if r.ok else {}
check('Gestor GET /agenda/url-agendamento → 200',
      r.status_code == 200, f"url={d_g.get('url')}")

# Super admin edita url_agendamento
nova_url = f'https://minha-barbearia.com/agendar/{slug}/'
r = requests.put(f'{BASE}/super/barbearias/{bid}', headers=h(sa),
    json={'url_agendamento': nova_url}, timeout=10)
check('Super admin PUT /super/barbearias/<id> com url_agendamento → 200',
      r.status_code == 200,
      f"url={r.json().get('barbearia',{}).get('url_agendamento')}")

# Verifica que a URL foi salva
r = requests.get(f'{BASE}/super/barbearias/lista', headers=h(sa), timeout=10)
barb_upd = next((b for b in r.json() if b.get('id') == bid), None)
check('GET /super/barbearias/lista retorna url_agendamento atualizada',
      barb_upd and barb_upd.get('url_agendamento') == nova_url,
      f"url={barb_upd.get('url_agendamento') if barb_upd else 'NAO ENCONTRADO'}")

# Barbeiro vê a URL atualizada
r = requests.get(f'{BASE}/agenda/url-agendamento', headers=h(bt), timeout=10)
d2 = r.json() if r.ok else {}
check('Barbeiro vê URL atualizada após edição do super admin',
      d2.get('url') == nova_url, f"url={d2.get('url')}")

# Gestor vê a URL atualizada
r = requests.get(f'{BASE}/agenda/url-agendamento', headers=h(gt), timeout=10)
d3 = r.json() if r.ok else {}
check('Gestor vê URL atualizada após edição do super admin',
      d3.get('url') == nova_url, f"url={d3.get('url')}")

# Resetar para padrão (url_agendamento = null → usa /b/{slug}/)
r = requests.put(f'{BASE}/super/barbearias/{bid}', headers=h(sa),
    json={'url_agendamento': ''}, timeout=10)
r2 = requests.get(f'{BASE}/agenda/url-agendamento', headers=h(bt), timeout=10)
check('Resetar url_agendamento para vazio → volta para padrão /b/{slug}/',
      r2.json().get('url') == f'/b/{slug}/',
      f"url={r2.json().get('url')}")

print('\n  3. HTML — banner e modal:')

# Barbeiro produtos: sem CRUD
r = requests.get(f'{BASE}/barbeiro/produtos', timeout=10)
sem_crud = 'formProd' not in r.text and 'salvarProd' not in r.text and 'api.produtos.criar' not in r.text
check('barbeiro/produtos.html: sem CRUD (read-only)',
      sem_crud and r.status_code == 200, f"bytes={len(r.content)}")

# Barbeiro produtos: tem tabela e busca
tem_view = 'pBody' in r.text and 'busca' in r.text
check('barbeiro/produtos.html: tem tabela e busca', tem_view)

# Gestor produtos: tem CRUD com modal (não usa confirm())
r = requests.get(f'{BASE}/gestor/produtos', timeout=10)
tem_modal = 'modalDel' in r.text and 'confirmarDel' in r.text and 'confirm(' not in r.text
check('gestor/produtos.html: modal de confirmação (sem confirm() nativo)',
      tem_modal and r.status_code == 200)

# Booking banner presente nas páginas barbeiro
for path in ['/barbeiro/agenda', '/barbeiro/dashboard', '/barbeiro/produtos']:
    r = requests.get(f'{BASE}{path}', timeout=10)
    tem_banner = 'bkBar' in r.text and 'urlAgendamento' in r.text
    check(f'{path}: banner booking presente', tem_banner)

# Booking banner presente nas páginas gestor
for path in ['/gestor/agenda', '/gestor/dashboard']:
    r = requests.get(f'{BASE}{path}', timeout=10)
    tem_banner = 'bkBar' in r.text and 'urlAgendamento' in r.text
    check(f'{path}: banner booking presente', tem_banner)

# Super admin barbearias: campo url_agendamento no modal
r = requests.get(f'{BASE}/super/barbearias', timeout=10)
tem_campo = 'fUrlAg' in r.text and 'url_agendamento' in r.text
check('super/barbearias.html: campo url_agendamento no modal', tem_campo)

print(f'\n{"="*62}')
print(f'  RESULTADO: {ok_c}/{ok_c+fail_c} OK  |  {fail_c} falha(s)')
print(f'{"="*62}\n')
sys.exit(0 if fail_c == 0 else 1)
