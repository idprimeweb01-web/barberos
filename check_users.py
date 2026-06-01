from app import create_app
from app.models import Usuario

app = create_app()
with app.app_context():
    users = Usuario.query.all()
    print(f"Total de usuários: {len(users)}")
    for u in users:
        print(f"  - {u.email} ({u.perfil})")
