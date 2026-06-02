import os
print(f"DATABASE_URL = {repr(os.getenv('DATABASE_URL'))}")
print(f"FLASK_APP = {repr(os.getenv('FLASK_APP'))}")

from app import create_app

app = create_app()

@app.route('/test')
def test():
    return {'status': 'ok'}, 200

if __name__ == "__main__":
    app.run()
