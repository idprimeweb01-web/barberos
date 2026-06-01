from app import create_app, db
from app.models import Usuario
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    user = Usuario.query.filter_by(email="adm@barbearia.com").first()
    if user:
        user.senha = generate_password_hash("senha123")
        db.session.commit()
        print("✅ Senha resetada para 'senha123'")
    else:
        print("Usuário não encontrado!")
