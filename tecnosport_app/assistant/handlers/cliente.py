from typing import Optional
from repository import cliente_repo


def buscar_clientes(query: str) -> list[dict]:
    results = cliente_repo.buscar(query)
    return [
        {
            "id": c.id,
            "nombre": c.nombre,
            "telefono": c.telefono or "",
            "saldo": float(c.saldo),
            "dias_sin_abonar": c.dias_sin_abonar,
        }
        for c in results
    ]


def obtener_saldo(cliente_id: str) -> Optional[dict]:
    c = cliente_repo.get_by_id(cliente_id)
    if not c:
        return None
    return {
        "nombre": c.nombre,
        "saldo": float(c.saldo),
        "total_prestado": float(c.total_prestado),
        "total_abonado": float(c.total_abonado),
        "dias_sin_abonar": c.dias_sin_abonar,
        "ultimo_abono": {
            "fecha": c.ultimo_abono.fecha,
            "monto": float(c.ultimo_abono.monto),
        } if c.ultimo_abono else None,
    }


def obtener_ficha(cliente_id: str) -> Optional[dict]:
    from database import db
    c = cliente_repo.get_by_id(cliente_id)
    if not c:
        return None
    return {
        "id": c.id,
        "nombre": c.nombre,
        "telefono": c.telefono or "",
        "fecha_creacion": c.fecha_creacion,
        "activo": c.activo,
        "saldo": float(c.saldo),
    }


def obtener_historial(cliente_id: str) -> Optional[list]:
    from database import db
    try:
        movs = db.get_movimientos_by_cliente(cliente_id)
        return [
            {
                "tipo": m["tipo"],
                "descripcion": m.get("descripcion", ""),
                "monto": float(m["monto"]),
                "fecha": m["fecha"],
            }
            for m in sorted(movs, key=lambda x: x.get("timestamp", ""), reverse=True)
        ]
    except Exception:
        return []


def obtener_ultimos_pagos(cliente_id: str, limite: int = 5) -> list:
    from database import db
    try:
        movs = db.get_movimientos_by_cliente(cliente_id)
        abonos = [m for m in movs if m["tipo"] == "abono"]
        abonos.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return [
            {
                "monto": float(m["monto"]),
                "fecha": m["fecha"],
                "descripcion": m.get("descripcion", ""),
            }
            for m in abonos[:limite]
        ]
    except Exception:
        return []


def obtener_prestamos(cliente_id: str, limite: int = 10) -> list:
    from database import db
    try:
        movs = db.get_movimientos_by_cliente(cliente_id)
        prestamos = [m for m in movs if m["tipo"] == "prestamo"]
        prestamos.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return [
            {
                "monto": float(m["monto"]),
                "fecha": m["fecha"],
                "descripcion": m.get("descripcion", ""),
            }
            for m in prestamos[:limite]
        ]
    except Exception:
        return []


def obtener_resumen(cliente_id: str) -> Optional[dict]:
    c = cliente_repo.get_by_id(cliente_id)
    if not c:
        return None
    pagos = obtener_ultimos_pagos(cliente_id, 3)
    prestamos = obtener_prestamos(cliente_id, 3)
    return {
        "nombre": c.nombre,
        "saldo": float(c.saldo),
        "total_prestado": float(c.total_prestado),
        "total_abonado": float(c.total_abonado),
        "dias_sin_abonar": c.dias_sin_abonar,
        "ultimos_pagos": pagos,
        "ultimos_prestamos": prestamos,
    }