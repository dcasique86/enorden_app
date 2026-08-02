from decimal import Decimal
from schemas import ProveedorCreate, ProveedorUpdate


class TestProveedorCrud:

    def test_crear_proveedor(self, db, proveedor_repo):
        data = ProveedorCreate(nombre="Distribuidora ABC", telefono="3110001111")
        result = proveedor_repo.create(data)
        assert result.nombre == "Distribuidora ABC"
        assert result.telefono == "3110001111"
        assert result.saldo == Decimal("0.00")
        assert result.activo is True

    def test_crear_proveedor_sin_telefono(self, db, proveedor_repo):
        data = ProveedorCreate(nombre="Mayorista SAS")
        result = proveedor_repo.create(data)
        assert result.telefono == ""

    def test_get_all_proveedores(self, db, proveedor_repo):
        proveedor_repo.create(ProveedorCreate(nombre="Prov 1"))
        proveedor_repo.create(ProveedorCreate(nombre="Prov 2"))
        proveedor_repo.create(ProveedorCreate(nombre="Prov 3"))
        todos = proveedor_repo.get_all()
        assert len(todos) == 3

    def test_get_all_vacio(self, db, proveedor_repo):
        assert proveedor_repo.get_all() == []

    def test_get_by_id(self, db, proveedor_repo):
        creado = proveedor_repo.create(ProveedorCreate(nombre="Comercial XYZ"))
        encontrado = proveedor_repo.get_by_id(creado.id)
        assert encontrado is not None
        assert encontrado.nombre == "Comercial XYZ"

    def test_get_by_id_inexistente(self, db, proveedor_repo):
        assert proveedor_repo.get_by_id("no-existe") is None

    def test_actualizar_proveedor(self, db, proveedor_repo):
        creado = proveedor_repo.create(ProveedorCreate(nombre="Viejo", telefono="111"))
        ok = proveedor_repo.update(creado.id, ProveedorUpdate(nombre="Nuevo", telefono="222"))
        assert ok is True
        encontrado = proveedor_repo.get_by_id(creado.id)
        assert encontrado.nombre == "Nuevo"

    def test_actualizar_parcial(self, db, proveedor_repo):
        creado = proveedor_repo.create(ProveedorCreate(nombre="SoloTel", telefono="555"))
        proveedor_repo.update(creado.id, ProveedorUpdate(telefono="666"))
        encontrado = proveedor_repo.get_by_id(creado.id)
        assert encontrado.nombre == "SoloTel"
        assert encontrado.telefono == "666"

    def test_eliminar_proveedor(self, db, proveedor_repo):
        creado = proveedor_repo.create(ProveedorCreate(nombre="Eliminar"))
        ok = proveedor_repo.delete(creado.id)
        assert ok is True
        encontrado = proveedor_repo.get_by_id(creado.id)
        assert encontrado is not None
        assert encontrado.activo is False

    def test_eliminar_inexistente(self, db, proveedor_repo):
        assert proveedor_repo.delete("no-existe") is False

    def test_buscar_proveedor(self, db, proveedor_repo):
        proveedor_repo.create(ProveedorCreate(nombre="Ferretería El Tornillo"))
        proveedor_repo.create(ProveedorCreate(nombre="Ferretería La Tuerca"))
        resultados = proveedor_repo.buscar("Tornillo")
        assert len(resultados) == 1
        assert resultados[0].nombre == "Ferretería El Tornillo"

    def test_buscar_sin_resultados(self, db, proveedor_repo):
        assert proveedor_repo.buscar("ZZZZZ") == []

    def test_saldo_proveedor_con_facturas(self, db, proveedor_repo):
        p = proveedor_repo.create(ProveedorCreate(nombre="Acreedor"))
        db.crear_movimiento_proveedor(proveedor_id=p.id, tipo="factura", descripcion="F1", monto=200000)

        resumen = db.get_resumen_proveedor(p.id)
        assert resumen["total_facturas"] == 200000.0
        assert resumen["saldo"] == 200000.0

    def test_saldo_con_pagos(self, db, proveedor_repo):
        p = proveedor_repo.create(ProveedorCreate(nombre="Pagado"))
        db.crear_movimiento_proveedor(proveedor_id=p.id, tipo="factura", descripcion="F1", monto=300000)
        db.crear_movimiento_proveedor(proveedor_id=p.id, tipo="pago", descripcion="P1", monto=100000)

        resumen = db.get_resumen_proveedor(p.id)
        assert resumen["total_facturas"] == 300000.0
        assert resumen["total_pagado"] == 100000.0
        assert resumen["saldo"] == 200000.0
