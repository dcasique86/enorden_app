from typing import Optional


SEARCH_KEYWORDS = ["buscar", "busca", "encuentra", "encuentre", "quien es", "dime de"]
SALDO_KEYWORDS = ["saldo", "deuda", "cuanto debe", "balance"]
HISTORIAL_KEYWORDS = ["historial", "historia", "movimientos", "movimiento", "actividad"]
PAGOS_KEYWORDS = ["pagos", "abonos", "pago", "abono", "ultimo pago", "ultimos pagos"]
PRESTAMOS_KEYWORDS = ["prestamos", "prestamo", "creditos", "credito"]
RESUMEN_KEYWORDS = ["resumen", "resume", "general", "completo", "todo"]
FICHA_KEYWORDS = ["ficha", "perfil", "abrir", "detalle", "informacion"]


def detect_intent(text: str) -> str:
    lowered = text.lower().strip()

    if lowered in ("saldo", "deuda", "balance"):
        return "saldo"
    if lowered in ("historial", "historial completo", "movimientos"):
        return "historial"
    if lowered in ("pagos", "abonos", "ultimos pagos"):
        return "pagos"
    if lowered in ("prestamos", "creditos"):
        return "prestamos"
    if lowered in ("resumen", "general", "completo"):
        return "resumen"
    if lowered in ("ficha", "perfil", "detalle", "abrir ficha"):
        return "ficha"

    for kw in RESUMEN_KEYWORDS:
        if kw in lowered:
            return "resumen"
    for kw in SALDO_KEYWORDS:
        if kw in lowered:
            return "saldo"
    for kw in HISTORIAL_KEYWORDS:
        if kw in lowered:
            return "historial"
    for kw in PAGOS_KEYWORDS:
        if kw in lowered:
            return "pagos"
    for kw in PRESTAMOS_KEYWORDS:
        if kw in lowered:
            return "prestamos"
    for kw in FICHA_KEYWORDS:
        if kw in lowered:
            return "ficha"

    return "buscar_cliente"


def detect_cliente_name(text: str, search_results: list) -> Optional[str]:
    lowered = text.lower().strip()
    for c in search_results:
        if c.get("nombre", "").lower() == lowered:
            return c["id"]
        if c.get("telefono", "").strip() == text.strip():
            return c["id"]
    return None