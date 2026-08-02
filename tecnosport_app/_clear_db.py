import sqlite3

conn = sqlite3.connect('datos_tecnosport.db')
cur = conn.cursor()
cur.execute("DELETE FROM clientes")
cur.execute("DELETE FROM movimientos")
cur.execute("DELETE FROM proveedores")
cur.execute("DELETE FROM movimientos_proveedores")
cur.execute("DELETE FROM gastos")
cur.execute("DELETE FROM productos")
cur.execute("DELETE FROM ventas")
cur.execute("DELETE FROM historial_precios")
cur.execute("DELETE FROM telegram_users")
cur.execute("DELETE FROM sqlite_sequence")
conn.commit()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print('RECUENTO TRAS BORRADO:')
for t in tables:
    count = cur.execute('SELECT COUNT(*) FROM "{}"'.format(t)).fetchone()[0]
    print('  {}: {}'.format(t, count))
conn.close()
