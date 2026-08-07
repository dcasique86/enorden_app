import io
import json

import pandas as pd
import pytest


def _payload(nombre="Camiseta", codigo=None, **kwargs):
    payload = {
        "nombre": nombre,
        "categoria": kwargs.get("categoria", "Ropa"),
        "precio_compra": kwargs.get("precio_compra", 1000),
        "precio_venta": kwargs.get("precio_venta", 2500),
        "stock": kwargs.get("stock", 5),
        "stock_minimo": kwargs.get("stock_minimo", 0),
    }
    if kwargs.get("referencia") is not None:
        payload["referencia"] = kwargs["referencia"]
    if codigo is not None:
        payload["codigo_barras"] = codigo
    return payload


def _crear_y_obtener(client, payload):
    resp = client.post("/api/productos", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _xlsx_bytes(filas):
    buf = io.BytesIO()
    pd.DataFrame(filas).to_excel(buf, index=False)
    buf.seek(0)
    return buf


MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class TestCrearProducto:

    def test_crear_basico(self, client):
        data = _crear_y_obtener(client, _payload())
        assert data["nombre"] == "Camiseta"
        assert data["codigo_barras"] is None
        assert data["activo"] is True

    def test_crear_normaliza_codigo(self, client):
        data = _crear_y_obtener(client, _payload(codigo="  7701234567890  "))
        assert data["codigo_barras"] == "7701234567890"

    def test_crear_sin_nombre_400(self, client):
        resp = client.post("/api/productos", json=_payload(nombre="   "))
        assert resp.status_code == 400
        assert "nombre" in resp.json()["detail"].lower()

    def test_crear_precio_negativo_400(self, client):
        resp = client.post("/api/productos", json=_payload(precio_venta=-5))
        assert resp.status_code == 400

    def test_crear_codigo_duplicado_409(self, client):
        _crear_y_obtener(client, _payload(codigo="7701234567890"))
        resp = client.post("/api/productos", json=_payload(nombre="Otra", codigo="7701234567890"))
        assert resp.status_code == 409
        assert "código de barras" in resp.json()["detail"].lower()


class TestLeerProductos:

    def test_listar_productos(self, client):
        _crear_y_obtener(client, _payload(nombre="A"))
        _crear_y_obtener(client, _payload(nombre="B"))
        resp = client.get("/api/productos")
        assert resp.status_code == 200
        nombres = [p["nombre"] for p in resp.json()["data"]]
        assert set(nombres) == {"A", "B"}

    def test_get_detalle_200(self, client):
        creado = _crear_y_obtener(client, _payload(codigo="7701234567890"))
        resp = client.get(f"/api/productos/{creado['id']}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == creado["id"]
        assert data["codigo_barras"] == "7701234567890"
        assert "movimientos" in data

    def test_get_detalle_404(self, client):
        resp = client.get("/api/productos/no-existe")
        assert resp.status_code == 404

    def test_buscar_por_codigo_200(self, client):
        _crear_y_obtener(client, _payload(codigo="7701234567890"))
        resp = client.get("/api/productos/buscar-por-codigo", params={"codigo": "7701234567890"})
        assert resp.status_code == 200
        assert resp.json()["data"]["codigo_barras"] == "7701234567890"

    def test_buscar_por_codigo_404(self, client):
        resp = client.get("/api/productos/buscar-por-codigo", params={"codigo": "999999999"})
        assert resp.status_code == 404

    def test_buscar_general_por_codigo(self, client):
        _crear_y_obtener(client, _payload(nombre="Zapato", codigo="7701234567890"))
        resp = client.get("/api/productos/buscar", params={"q": "7701234567"})
        assert resp.status_code == 200
        assert any(p["nombre"] == "Zapato" for p in resp.json()["data"])


class TestActualizarProducto:

    def test_actualizar_datos_200(self, client):
        creado = _crear_y_obtener(client, _payload())
        resp = client.put(f"/api/productos/{creado['id']}", json={"nombre": "Nuevo", "precio_venta": 9999})
        assert resp.status_code == 200
        detalle = client.get(f"/api/productos/{creado['id']}").json()["data"]
        assert detalle["nombre"] == "Nuevo"
        assert detalle["precio_venta"] == 9999

    def test_actualizar_codigo_200(self, client):
        creado = _crear_y_obtener(client, _payload())
        resp = client.put(f"/api/productos/{creado['id']}", json={"codigo_barras": "7790000000001"})
        assert resp.status_code == 200
        detalle = client.get(f"/api/productos/{creado['id']}").json()["data"]
        assert detalle["codigo_barras"] == "7790000000001"

    def test_actualizar_codigo_normaliza(self, client):
        creado = _crear_y_obtener(client, _payload())
        client.put(f"/api/productos/{creado['id']}", json={"codigo_barras": "  7790000000001  "})
        detalle = client.get(f"/api/productos/{creado['id']}").json()["data"]
        assert detalle["codigo_barras"] == "7790000000001"

    def test_actualizar_mismo_codigo_200(self, client):
        creado = _crear_y_obtener(client, _payload(codigo="7701234567890"))
        resp = client.put(f"/api/productos/{creado['id']}", json={"codigo_barras": "7701234567890"})
        assert resp.status_code == 200

    def test_actualizar_codigo_repetido_409(self, client):
        a = _crear_y_obtener(client, _payload(nombre="A", codigo="7701234567890"))
        b = _crear_y_obtener(client, _payload(nombre="B", codigo="7790000000001"))
        resp = client.put(f"/api/productos/{b['id']}", json={"codigo_barras": "7701234567890"})
        assert resp.status_code == 409
        detalle = client.get(f"/api/productos/{a['id']}").json()["data"]
        assert detalle["codigo_barras"] == "7701234567890"

    def test_actualizar_limpiar_codigo(self, client):
        creado = _crear_y_obtener(client, _payload(codigo="7701234567890"))
        resp = client.put(f"/api/productos/{creado['id']}", json={"codigo_barras": ""})
        assert resp.status_code == 200
        detalle = client.get(f"/api/productos/{creado['id']}").json()["data"]
        assert detalle["codigo_barras"] is None

    def test_actualizar_404(self, client):
        resp = client.put("/api/productos/no-existe", json={"nombre": "X"})
        assert resp.status_code == 404


class TestEliminarProducto:

    def test_eliminar_cierra_codigo(self, client):
        creado = _crear_y_obtener(client, _payload(codigo="7701234567890"))
        resp = client.delete(f"/api/productos/{creado['id']}")
        assert resp.status_code == 200
        lista = client.get("/api/productos").json()["data"]
        assert all(p["id"] != creado["id"] for p in lista)
        assert client.get("/api/productos/buscar-por-codigo", params={"codigo": "7701234567890"}).status_code == 404

    def test_eliminar_404(self, client):
        resp = client.delete("/api/productos/no-existe")
        assert resp.status_code == 404


class TestExportarProductos:

    def test_exportar_genera_excel_con_codigos(self, client):
        _crear_y_obtener(client, _payload(nombre="Zapato", codigo="7701234567890"))
        resp = client.get("/api/productos/exportar")
        assert resp.status_code == 200
        assert "spreadsheetml" in resp.headers["content-type"]
        df = pd.read_excel(io.BytesIO(resp.content), dtype=str)
        assert "Código de barras" in list(df.columns)
        fila = df[df["Nombre"] == "Zapato"]
        assert len(fila) == 1
        assert fila.iloc[0]["Código de barras"] == "7701234567890"

    def test_exportar_producto_sin_codigo_con_vacio(self, client):
        _crear_y_obtener(client, _payload(nombre="SinCodigo"))
        df = pd.read_excel(io.BytesIO(client.get("/api/productos/exportar").content))
        fila = df[df["Nombre"] == "SinCodigo"]
        assert pd.isna(fila.iloc[0]["Código de barras"]) or fila.iloc[0]["Código de barras"] == ""


class TestImportarProductos:

    def _files(self, buf, nombre="productos.xlsx"):
        return {"file": (nombre, buf, MIME_XLSX)}

    def test_preview_200(self, client):
        buf = _xlsx_bytes([
            {"Nombre": "A", "Código de barras": "7711111111111"},
            {"Nombre": "B", "Código de barras": "7711111111112"},
        ])
        resp = client.post("/api/productos/importar/preview", files=self._files(buf))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_filas"] == 2
        assert "Código de barras" in data["columnas"]

    def test_preview_archivo_no_excel_400(self, client):
        resp = client.post("/api/productos/importar/preview", files={"file": ("datos.txt", io.BytesIO(b"hola"), "text/plain")})
        assert resp.status_code == 400

    def test_importar_3_productos(self, client):
        buf = _xlsx_bytes([
            {"nombre": "Import A", "categoria": "T", "referencia": "R1", "codigo": "7711111111111", "compra": 100, "venta": 200, "stock": 5},
            {"nombre": "Import B", "categoria": "T", "referencia": "R2", "codigo": "7711111111112", "compra": 200, "venta": 400, "stock": 3},
            {"nombre": "Import C", "categoria": "T", "referencia": "R3", "codigo": "7711111111113", "compra": 300, "venta": 600, "stock": 1},
        ])
        config = {
            "col_nombre": "nombre",
            "col_categoria": "categoria",
            "col_referencia": "referencia",
            "col_codigo_barras": "codigo",
            "col_precio_compra": "compra",
            "col_precio_venta": "venta",
            "col_stock": "stock",
            "crear_backup": False,
        }
        resp = client.post("/api/productos/importar", files=self._files(buf), data={"config": json.dumps(config)})
        assert resp.status_code == 200, resp.text
        body = resp.json()["data"]
        assert body["importados"] == 3
        assert body["errores"] == []
        lista = client.get("/api/productos").json()["data"]
        codigos = {p["nombre"]: p["codigo_barras"] for p in lista}
        assert codigos["Import A"] == "7711111111111"
        assert codigos["Import C"] == "7711111111113"

    def test_importar_codigo_normalizado(self, client):
        buf = _xlsx_bytes([
            {"nombre": "Con Espacios", "codigo": "  7711111111111  "},
        ])
        config = {"col_nombre": "nombre", "col_codigo_barras": "codigo", "crear_backup": False}
        resp = client.post("/api/productos/importar", files=self._files(buf), data={"config": json.dumps(config)})
        assert resp.status_code == 200
        lista = client.get("/api/productos").json()["data"]
        assert next(p for p in lista if p["nombre"] == "Con Espacios")["codigo_barras"] == "7711111111111"

    def test_importar_duplicado_informa_error(self, client):
        buf = _xlsx_bytes([
            {"nombre": "A", "codigo": "7711111111111"},
            {"nombre": "B", "codigo": "7711111111111"},
        ])
        config = {"col_nombre": "nombre", "col_codigo_barras": "codigo", "crear_backup": False}
        resp = client.post("/api/productos/importar", files=self._files(buf), data={"config": json.dumps(config)})
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["importados"] == 1
        assert len(body["errores"]) == 1
        assert "código de barras" in body["errores"][0].lower()

    def test_importar_sin_nombre_400(self, client):
        buf = _xlsx_bytes([{"nombre": "A"}])
        resp = client.post("/api/productos/importar", files=self._files(buf), data={"config": json.dumps({"crear_backup": False})})
        assert resp.status_code == 400

    def test_importar_interfaz_con_codigo_previo_respetado(self, client):
        _crear_y_obtener(client, _payload(nombre="Existente", codigo="7711111111111"))
        buf = _xlsx_bytes([
            {"nombre": "Nuevo A", "codigo": "7711111111111"},
            {"nombre": "Nuevo B", "codigo": "7711111111112"},
        ])
        config = {"col_nombre": "nombre", "col_codigo_barras": "codigo", "crear_backup": False}
        resp = client.post("/api/productos/importar", files=self._files(buf), data={"config": json.dumps(config)})
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["importados"] == 1
        assert len(body["errores"]) == 1