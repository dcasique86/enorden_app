from typing import Optional
from datetime import datetime


class UIRenderer:
    @staticmethod
    def render_saldo(data: dict, cliente_nombre: str) -> str:
        estado = "🟢" if data["saldo"] == 0 else "🟡" if data["saldo"] < 500000 else "🔴"
        rows = [
            f"**{cliente_nombre}** — Saldo",
            f"{estado} Saldo actual: `${data['saldo']:,.0f}`".replace(",", "."),
            f"💰 Total prestado: `${data['total_prestado']:,.0f}`".replace(",", "."),
            f"💳 Total abonado: `${data['total_abonado']:,.0f}`".replace(",", "."),
        ]
        if data.get("dias_sin_abonar") is not None:
            rows.append(f"📅 Días sin abonar: **{data['dias_sin_abonar']}**")
        if data.get("ultimo_abono"):
            rows.append(f"Último abono: `${data['ultimo_abono']['monto']:,.0f}`".replace(",", ".") + f" ({data['ultimo_abono']['fecha']})")
        return "\n".join(rows)

    @staticmethod
    def render_historial(data: list, cliente_nombre: str) -> str:
        if not data:
            return f"**{cliente_nombre}** — Sin movimientos registrados."
        lines = [f"**{cliente_nombre}** — Historial ({len(data)} movimientos):"]
        for m in data[:15]:
            icono = "📤" if m["tipo"] == "prestamo" else "📥"
            monto_str = f"`${m['monto']:,.0f}`".replace(",", ".")
            lines.append(f"{icono} {m['fecha']} — {monto_str} — {m.get('descripcion', '-')}")
        if len(data) > 15:
            lines.append(f"_...y {len(data) - 15} movimientos más_")
        return "\n".join(lines)

    @staticmethod
    def render_pagos(data: list, cliente_nombre: str) -> str:
        if not data:
            return f"**{cliente_nombre}** — Sin pagos registrados."
        lines = [f"**{cliente_nombre}** — Últimos {len(data)} pagos:"]
        for p in data:
            monto_str = f"`${p['monto']:,.0f}`".replace(",", ".")
            lines.append(f"📥 {p['fecha']} — {monto_str} — {p.get('descripcion', '-')}")
        return "\n".join(lines)

    @staticmethod
    def render_prestamos(data: list, cliente_nombre: str) -> str:
        if not data:
            return f"**{cliente_nombre}** — Sin préstamos registrados."
        lines = [f"**{cliente_nombre}** — Últimos {len(data)} préstamos:"]
        for p in data:
            monto_str = f"`${p['monto']:,.0f}`".replace(",", ".")
            lines.append(f"📤 {p['fecha']} — {monto_str} — {p.get('descripcion', '-')}")
        return "\n".join(lines)

    @staticmethod
    def render_resumen(data: dict, cliente_nombre: str) -> str:
        lines = [
            f"**{cliente_nombre}** — Resumen",
            f"💰 Saldo: `${data['saldo']:,.0f}`".replace(",", "."),
            f"📤 Total prestado: `${data['total_prestado']:,.0f}`".replace(",", "."),
            f"📥 Total abonado: `${data['total_abonado']:,.0f}`".replace(",", "."),
        ]
        if data.get("dias_sin_abonar") is not None:
            lines.append(f"📅 Días sin abonar: **{data['dias_sin_abonar']}**")
        if data.get("ultimos_pagos"):
            lines.append("\n*Últimos pagos:*")
            for p in data["ultimos_pagos"]:
                lines.append(f"  📥 `${p['monto']:,.0f}`".replace(",", ".") + f" — {p['fecha']}")
        if data.get("ultimos_prestamos"):
            lines.append("\n*Últimos préstamos:*")
            for p in data["ultimos_prestamos"]:
                lines.append(f"  📤 `${p['monto']:,.0f}`".replace(",", ".") + f" — {p['fecha']}")
        return "\n".join(lines)

    @staticmethod
    def render_ficha(data: dict) -> str:
        estado = "🟢 Activo" if data["activo"] else "🔴 Inactivo"
        return (
            f"**{data['nombre']}** — Ficha\n"
            f"🆔 ID: `{data['id']}`\n"
            f"📞 Teléfono: {data.get('telefono', '-')}\n"
            f"📅 Creado: {data.get('fecha_creacion', '-')}\n"
            f"{estado}"
        )

    @staticmethod
    def render_cliente_lista(clientes: list, query: str) -> str:
        lines = [f"Encontré {len(clientes)} clientes para \"{query}\":"]
        for i, c in enumerate(clientes, 1):
            saldo_str = f"`${c['saldo']:,.0f}`".replace(",", ".")
            lines.append(f"{i}. **{c['nombre']}** — {saldo_str} — 📞 {c.get('telefono', '-')}")
        lines.append("\n_Escribe el número o nombre del cliente para seleccionarlo._")
        return "\n".join(lines)