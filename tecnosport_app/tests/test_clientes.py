from decimal import Decimal
from schemas import ClienteCreate, ClienteUpdate


class TestClienteCrud:

    def test_crear_cliente(self, db, cliente_repo):
        data = ClienteCreate(nombre="Juan Pérez", telefono="3001234567")
        result = cliente_repo.create(data)
        assert result.nombre == "Juan Pérez"
        assert result.telefono == "3001234567"
        assert result.saldo == Decimal("0.00")
        assert result.activo is True
        assert result.id is not None

    def test_crear_cliente_sin_telefono(self, db, cliente_repo):
        data = ClienteCreate(nombre="María López")
        result = cliente_repo.create(data)
        assert result.nombre == "María López"
        assert result.telefono == ""

    def test_get_all_clientes(self, db, cliente_repo):
        cliente_repo.create(ClienteCreate(nombre="Cliente A"))
        cliente_repo.create(ClienteCreate(nombre="Cliente B"))
        clientes = cliente_repo.get_all()
        assert len(clientes) == 2

    def test_get_all_vacio(self, db, cliente_repo):
        clientes = cliente_repo.get_all()
        assert clientes == []

    def test_get_by_id(self, db, cliente_repo):
        creado = cliente_repo.create(ClienteCreate(nombre="Carlos Ruiz"))
        encontrado = cliente_repo.get_by_id(creado.id)
        assert encontrado is not None
        assert encontrado.nombre == "Carlos Ruiz"
        assert encontrado.id == creado.id

    def test_get_by_id_inexistente(self, db, cliente_repo):
        result = cliente_repo.get_by_id("no-existe")
        assert result is None

    def test_actualizar_cliente(self, db, cliente_repo):
        creado = cliente_repo.create(ClienteCreate(nombre="Antiguo", telefono="111"))
        actualizado = cliente_repo.update(creado.id, ClienteUpdate(nombre="Nuevo", telefono="222"))
        assert actualizado is True
        encontrado = cliente_repo.get_by_id(creado.id)
        assert encontrado.nombre == "Nuevo"
        assert encontrado.telefono == "222"

    def test_actualizar_solo_nombre(self, db, cliente_repo):
        creado = cliente_repo.create(ClienteCreate(nombre="Original", telefono="555"))
        cliente_repo.update(creado.id, ClienteUpdate(nombre="SoloNombre"))
        encontrado = cliente_repo.get_by_id(creado.id)
        assert encontrado.nombre == "SoloNombre"
        assert encontrado.telefono == "555"  # no debe cambiar

    def test_eliminar_cliente(self, db, cliente_repo):
        creado = cliente_repo.create(ClienteCreate(nombre="Eliminar"))
        eliminado = cliente_repo.delete(creado.id)
        assert eliminado is True
        encontrado = cliente_repo.get_by_id(creado.id)
        assert encontrado is not None
        assert encontrado.activo is False

    def test_eliminar_inexistente(self, db, cliente_repo):
        result = cliente_repo.delete("no-existe")
        assert result is False

    def test_buscar_por_nombre(self, db, cliente_repo):
        cliente_repo.create(ClienteCreate(nombre="Pedro Infante"))
        cliente_repo.create(ClienteCreate(nombre="Pedro Pascal"))
        cliente_repo.create(ClienteCreate(nombre="María García"))

        resultados = cliente_repo.buscar("Pedro")
        assert len(resultados) == 2

    def test_buscar_por_telefono(self, db, cliente_repo):
        cliente_repo.create(ClienteCreate(nombre="Ana", telefono="3109998888"))
        resultados = cliente_repo.buscar("3109998888")
        assert len(resultados) == 1

    def test_buscar_sin_resultados(self, db, cliente_repo):
        resultados = cliente_repo.buscar("ZZZZZ")
        assert resultados == []

    def test_con_deuda(self, db, cliente_repo):
        c = cliente_repo.create(ClienteCreate(nombre="Deudor"))
        db.crear_movimiento(cliente_id=c.id, tipo="prestamo", descripcion="Prueba", monto=50000)

        deudores = cliente_repo.get_con_deuda()
        assert len(deudores) == 1
        assert deudores[0].nombre == "Deudor"
        assert deudores[0].saldo == Decimal("50000.00")

    def test_con_deuda_solo_mayor_cero(self, db, cliente_repo):
        c = cliente_repo.create(ClienteCreate(nombre="Deudor"))
        db.crear_movimiento(cliente_id=c.id, tipo="prestamo", descripcion="P1", monto=50000)
        db.crear_movimiento(cliente_id=c.id, tipo="abono", descripcion="A1", monto=50000)

        deudores = cliente_repo.get_con_deuda()
        assert len(deudores) == 0
