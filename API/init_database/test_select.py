import psycopg2

# Connexion (utilise tes paramètres)
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="airline_data",
    user="root",
    password="password_test"
)
cur = conn.cursor()

# On teste une jointure pour voir si les aéroports sont bien liés aux villes
query = """
select * from fact_matchs;
            """





cur.execute(query)
rows = cur.fetchall()

print(f"Résultats pour New York :")

for row in rows:
    print(*row, sep=" - ")

cur.close()
conn.close()