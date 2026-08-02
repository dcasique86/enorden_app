from decimal import Decimal


class TestDashboard:

    def test_dashboard_stats_vacio(self, db):
        stats = db.get_dashboard_stats()
        assert stats["total_prestado"] == 0.0
        assert stats["total_abonado"] == 0.0
        assert stats["deuda_activa"] == 0.0
        assert stats["clientes_activos"] == 0
        assert stats["prestamos_hoy"] == 0.0
        assert stats["abonos_hoy"] == 0.0
        assert stats["top_deudores"] == []
        assert stats["cola_cobro"] == []
        assert stats["clientes_sin_abonos"] == []
        assert stats["ultimos_abonos"] == []

    def test_dashboard_con_prestamo(self, db):
        c = db.crear_cliente(nombre="Cliente Deuda", telefono="111")
        db.crear_movimiento(cliente_id=c["id"], tipo="prestamo", descripcion="Prueba", monto=100000)

        stats = db.get_dashboard_stats()
        assert stats["total_prestado"] == 100000.0
        assert stats["deuda_activa"] == 100000.0
        assert stats["clientes_activos"] == 1
        assert len(stats["top_deudores"]) == 1
        assert stats["top_deudores"][0]["saldo"] == 100000.0

    def test_dashboard_con_prestamo_y_abono(self, db):
        c = db.crear_cliente(nombre="Cliente Medio", telefono="222")
        db.crear_movimiento(cliente_id=c["id"], tipo="prestamo", descripcion="P1", monto=200000)
        db.crear_movimiento(cliente_id=c["id"], tipo="abono", descripcion="A1", monto=50000)

        stats = db.get_dashboard_stats()
        assert stats["total_prestado"] == 200000.0
        assert stats["total_abonado"] == 50000.0
        assert stats["deuda_activa"] == 150000.0

    def test_dashboard_varios_clientes(self, db):
        c1 = db.crear_cliente(nombre="C1", telefono="1")
        c2 = db.crear_cliente(nombre="C2", telefono="2")
        db.crear_movimiento(cliente_id=c1["id"], tipo="prestamo", descripcion="P", monto=100000)
        db.crear_movimiento(cliente_id=c2["id"], tipo="prestamo", descripcion="P", monto=300000)

        stats = db.get_dashboard_stats()
        assert stats["clientes_activos"] == 2
        assert stats["total_prestado"] == 400000.0
        assert len(stats["top_deudores"]) == 2
        # El top debe estar ordenado por saldo descendente
        assert stats["top_deudores"][0]["saldo"] == 300000.0
        assert stats["top_deudores"][1]["saldo"] == 100000.0

    def test_dashboard_clientes_sin_abonos(self, db):
        c = db.crear_cliente(nombre="Sin Abonos", telefono="333")
        db.crear_movimiento(cliente_id=c["id"], tipo="prestamo", descripcion="P1", monto=50000)

        stats = db.get_dashboard_stats()
        assert len(stats["clientes_sin_abonos"]) >= 1
        assert stats["clientes_sin_abonos"][0]["dias"] == "Nunca"

    def test_dashboard_ultimos_abonos(self, db):
        c = db.crear_cliente(nombre="Abonador", telefono="444")
        db.crear_movimiento(cliente_id=c["id"], tipo="abono", descripcion="A1", monto=25000)

        stats = db.get_dashboard_stats()
        assert len(stats["ultimos_abonos"]) >= 1
        assert stats["ultimos_abonos"][0]["monto"] == 25000.0
        assert stats["ultimos_abonos"][0]["cliente_nombre"] == "Abonador"

    def test_dashboard_cola_cobro(self, db):
        c = db.crear_cliente(nombre="Moroso", telefono="555")
        db.crear_movimiento(cliente_id=c["id"], tipo="prestamo", descripcion="P", monto=100000)

        stats = db.get_dashboard_stats()
        assert len(stats["cola_cobro"]) == 1
        assert stats["cola_cobro"][0]["nombre"] == "Moroso"
        assert stats["cola_cobro"][0]["saldo"] == 100000.0

    def test_flujo_caja_vacio(self, db):
        resumen = db.obtener_resumen_caja_diaria()
        assert resumen["ventas_total"] == 0.0
        assert resumen["abonos_total"] == 0.0
        assert resumen["pagos_proveedores_total"] == 0.0
        assert resumen["gastos_total"] == 0.0
        assert resumen["efectivo_neto"] == 0.0
        assert "fecha" in resumen

    def test_flujo_caja_con_movimientos(self, db):
        c = db.crear_cliente(nombre="C", telefono="1")
        db.crear_movimiento(cliente_id=c["id"], tipo="abono", descripcion="Abono", monto=80000)

        resumen = db.obtener_resumen_caja_diaria()
        assert resumen["abonos_total"] == 80000.0
        assert resumen["efectivo_neto"] == 80000.0

    def test_flujo_caja_neto(self, db):
        c = db.crear_cliente(nombre="C", telefono="1")
        p = db.crear_proveedor(nombre="P", telefono="2")
        db.crear_movimiento(cliente_id=c["id"], tipo="abono", descripcion="Abono", monto=100000)
        db.registrar_gasto(categoria="Servicios", monto=30000, descripcion="Luz")

        resumen = db.obtener_resumen_caja_diaria()
        assert resumen["abonos_total"] == 100000.0
        assert resumen["gastos_total"] == 30000.0
        assert resumen["efectivo_neto"] == 70000.0

    def test_historial_cliente(self, db):
        c = db.crear_cliente(nombre="Historico", telefono="666")
        db.crear_movimiento(cliente_id=c["id"], tipo="prestamo", descripcion="P1", monto=150000)
        db.crear_movimiento(cliente_id=c["id"], tipo="abono", descripcion="A1", monto=30000)

        historial = db.get_historial_cliente(c["id"])
        assert historial is not None
        assert historial["cliente"]["nombre"] == "Historico"
        assert historial["resumen"]["saldo"] == 120000.0
        assert len(historial["movimientos"]) == 2

    def test_historial_cliente_inexistente(self, db):
        assert db.get_historial_cliente("no-existe") is None
