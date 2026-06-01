import json
from app import create_app

app = create_app()
cli = app.test_client()

credenciais = [
    ('adm@barbearia.com',      'senha123'),
    ('gestor@caio.com',        'senha123'),
    ('barbeiro@barbearia.com', 'senha123'),
]

for email, senha in credenciais:
    r = cli.post('/auth/login',
                 data=json.dumps({'email': email, 'senha': senha}),
                 headers={'Content-Type': 'application/json'})
    d = r.get_json()
    u = d.get('usuario', {})
    print(f"[{r.status_code}] {email}  ->  perfil={u.get('perfil')}  barbearia_id={u.get('barbearia_id')}")
