import os
import traceback

print(f"DATABASE_URL = {repr(os.getenv('DATABASE_URL'))}", flush=True)
print(f"FLASK_APP = {repr(os.getenv('FLASK_APP'))}", flush=True)

try:
    from app import create_app
    app = create_app()
    print("SUCCESS: app created OK", flush=True)
except Exception as e:
    print(f"FATAL ERROR during app creation: {e}", flush=True)
    traceback.print_exc()
    raise


@app.route('/test')
def test():
    return {'status': 'ok'}, 200


@app.cli.command('seed-admin')
def seed_admin():
    """Cria barbearia e usuário super_admin iniciais."""
    from app import db
    from app.models import Barbearia, Usuario
    from werkzeug.security import generate_password_hash

    with app.app_context():
        if not Barbearia.query.filter_by(slug='admin').first():
            b = Barbearia(nome='Admin', slug='admin')
            db.session.add(b)
            db.session.flush()
            barbearia_id = b.id
            print(f"Barbearia criada: id={barbearia_id}")
        else:
            barbearia_id = Barbearia.query.filter_by(slug='admin').first().id
            print(f"Barbearia já existe: id={barbearia_id}")

        if not Usuario.query.filter_by(email='adm@barbearia.com').first():
            u = Usuario(
                barbearia_id=barbearia_id,
                nome='Admin',
                telefone='00000000000',
                email='adm@barbearia.com',
                senha=generate_password_hash('123456'),
                perfil='super_admin',
                ativo=True,
            )
            db.session.add(u)
            db.session.commit()
            print("Usuário adm@barbearia.com criado com senha 123456")
        else:
            print("Usuário adm@barbearia.com já existe")


if __name__ == "__main__":
    app.run()
