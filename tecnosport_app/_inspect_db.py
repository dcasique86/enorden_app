import sqlite3

conn = sqlite3.connect('datos_tecnosport.db')
cur = conn.cursor()
cur.execute("SELECT * FROM config")
cols = [d[0] for d in cur.description]
for row in cur.fetchall():
    print(dict(zip(cols, row)))
conn.close()
