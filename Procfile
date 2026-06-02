release: FLASK_APP=wsgi flask db upgrade
web: FLASK_APP=wsgi gunicorn -w 2 -b 0.0.0.0:$PORT wsgi:app
