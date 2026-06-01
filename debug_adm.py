from app import create_app
from app.models import Usuario
from werkzeug.security import check_password_hash

app = create_app()
with app.app_context():
    user = Usuario.query.filter_by(email="adm@barbearia.com").first()
    if user:
        print(f"Email: {user.email}")
        print(f"Perfil: {user.perfil}")
        print(f"Hash: {user.senha[:50]}...")
        
        # Testa se a senha bate
        resultado = check_password_hash(user.senha, "senha123")
        print(f"Senha 'senha123' bate? {resultado}")
    else:
        print("Usuário não encontrado!")
