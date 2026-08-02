from datetime import datetime, timedelta
from typing import Optional
from core.enums import TipoOperacion, EstadoOperacion


class PrestamoService:
    """Servicio único para toda la lógica de préstamos de mercancía.
    Dashboard, Telegram, Asistente EnOrden y futuros módulos
    deben consumir este servicio en lugar de acceder a la BD directamente.
    """

    def __init__(self, db_instance):
        self._db = db_instance

    # ── Consultas ──────────────────────────────────────────────

    def obtener_pendientes(self) -> list[dict]:
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT m.*, c.nombre as cliente_nombre "
                "FROM movimientos m "
                "JOIN clientes c ON c.id = m.cliente_id "
                "WHERE m.tipo_operacion = ? AND m.estado_operacion = ? "
                "ORDER BY m.fecha_vencimiento ASC",
                (TipoOperacion.PRESTAMO_MERCANCIA.value, EstadoOperacion.PENDIENTE.value),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def contar_pendientes(self) -> dict:
        """Retorna conteos para la tarjeta del Dashboard."""
        now = datetime.now()
        hoy = now.strftime("%Y-%m-%d")

        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT COUNT(*) FROM movimientos "
                "WHERE tipo_operacion = ? AND estado_operacion = ?",
                (TipoOperacion.PRESTAMO_MERCANCIA.value, EstadoOperacion.PENDIENTE.value),
            )
            total_pendientes = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM movimientos "
                "WHERE tipo_operacion = ? AND estado_operacion = ? "
                "AND fecha_vencimiento = ?",
                (TipoOperacion.PRESTAMO_MERCANCIA.value, EstadoOperacion.PENDIENTE.value, hoy),
            )
            vencen_hoy = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM movimientos "
                "WHERE tipo_operacion = ? AND estado_operacion = ? "
                "AND fecha_vencimiento < ?",
                (TipoOperacion.PRESTAMO_MERCANCIA.value, EstadoOperacion.PENDIENTE.value, hoy),
            )
            vencidos = cursor.fetchone()[0]

            return {
                "pendientes": total_pendientes,
                "vencen_hoy": vencen_hoy,
                "vencidos": vencidos,
            }
        finally:
            conn.close()

    # ── Automatización de vencimientos ─────────────────────────

    def verificar_vencimientos(self) -> int:
        """Convierte automáticamente préstamos vencidos a COMPRA.
        NO modifica saldo, inventario ni movimientos.
        Solo cambia estado_operacion de PENDIENTE a COMPRA.
        Retorna cantidad de conversiones realizadas.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE movimientos "
                "SET estado_operacion = ?, "
                "    descripcion = descripcion || ' [Convertido automáticamente a Compra: " + now + "]' "
                "WHERE tipo_operacion = ? "
                "AND estado_operacion = ? "
                "AND fecha_vencimiento IS NOT NULL "
                "AND fecha_vencimiento < date('now')",
                (
                    EstadoOperacion.COMPRA.value,
                    TipoOperacion.PRESTAMO_MERCANCIA.value,
                    EstadoOperacion.PENDIENTE.value,
                ),
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    # ── Devolución ─────────────────────────────────────────────

    def registrar_devolucion(self, movimiento_id: str) -> Optional[dict]:
        """Registra la devolución de un préstamo de mercancía.
        Solo disponible si estado_operacion = PENDIENTE.
        NO modifica inventario (se hará en fase posterior).
        """
        conn = self._db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM movimientos WHERE id = ?",
                (movimiento_id,),
            )
            mov = cursor.fetchone()
            if not mov:
                return None

            mov = dict(mov)
            if mov.get("estado_operacion") != EstadoOperacion.PENDIENTE.value:
                return None

            cursor.execute(
                "UPDATE movimientos SET estado_operacion = ? WHERE id = ?",
                (EstadoOperacion.DEVUELTO.value, movimiento_id),
            )
            conn.commit()

            cursor.execute(
                "SELECT m.*, c.nombre as cliente_nombre "
                "FROM movimientos m "
                "JOIN clientes c ON c.id = m.cliente_id "
                "WHERE m.id = ?",
                (movimiento_id,),
            )
            return dict(cursor.fetchone())
        finally:
            conn.close()

    # ── Creación ───────────────────────────────────────────────

    @staticmethod
    def calcular_fecha_vencimiento(fecha_movimiento: Optional[str] = None) -> str:
        """Calcula fecha_vencimiento como fecha_movimiento + 48 horas."""
        if fecha_movimiento:
            base = datetime.strptime(fecha_movimiento, "%Y-%m-%d")
        else:
            base = datetime.now()
        return (base + timedelta(hours=48)).strftime("%Y-%m-%d")

    @staticmethod
    def determinar_estado_inicial(tipo_operacion: str) -> str:
        if tipo_operacion == TipoOperacion.PRESTAMO_MERCANCIA.value:
            return EstadoOperacion.PENDIENTE.value
        return EstadoOperacion.COMPRA.value
