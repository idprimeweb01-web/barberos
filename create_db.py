import psycopg2

try:
    conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='barberos123', dbname='postgres')
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT datname FROM pg_database WHERE datname = 'barberos'")
    exists = cur.fetchone()
    if exists:
        print('Banco barberos ja existe')
    else:
        cur.execute('CREATE DATABASE barberos')
        print('Banco barberos criado com sucesso')
    cur.close()
    conn.close()
except Exception as e:
    print(f'Erro: {e}')
