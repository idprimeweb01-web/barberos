import psycopg2

conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='barberos123', dbname='barbeiros')
cur = conn.cursor()
cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
tabelas = cur.fetchall()
print(f"Banco: barbeiros | Total de tabelas: {len(tabelas)}")
for t in tabelas:
    print(f"  - {t[0]}")
cur.close()
conn.close()
