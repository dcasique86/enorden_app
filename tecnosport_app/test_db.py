import sqlite3
import os
from database import db
from schemas import GastoCreate
from repository import gasto_repo

# 1. Probar gasto_repo
gasto = GastoCreate(categoria="Transporte", monto=15000, descripcion="Taxi")
gasto_res = gasto_repo.create(gasto)
print("Gasto Creado:", gasto_res)

# 2. Probar flujo-caja
flujo = gasto_repo.obtener_resumen_caja_diaria()
print("Flujo de Caja:", flujo)

# 3. Probar Trigger historial_precios
conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "datos_tecnosport.db"))
cursor = conn.cursor()

# Insertar un producto dummy
cursor.execute("INSERT OR REPLACE INTO productos (id, nombre, precio_compra, precio_venta) VALUES ('PROD_TEST', 'Test Producto', 100, 200)")
conn.commit()

# Actualizar precio para disparar el trigger
cursor.execute("UPDATE productos SET precio_compra = 150, precio_venta = 250 WHERE id = 'PROD_TEST'")
conn.commit()

# Verificar tabla historial_precios
cursor.execute("SELECT * FROM historial_precios WHERE producto_id = 'PROD_TEST'")
rows = cursor.fetchall()
print("Historial de Precios Trigger result:")
for r in rows:
    print(r)

# Cleanup
cursor.execute("DELETE FROM productos WHERE id = 'PROD_TEST'")
cursor.execute("DELETE FROM historial_precios WHERE producto_id = 'PROD_TEST'")
conn.commit()
conn.close()
