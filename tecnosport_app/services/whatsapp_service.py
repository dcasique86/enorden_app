"""
Servicio de notificaciones WhatsApp vía Meta Cloud API
Configuración vía variables de entorno:
  WA_API_TOKEN=EAAR... (token de acceso)
  WA_PHONE_NUMBER_ID=123456... (ID del número de teléfono)
  WA_API_VERSION=v21.0
"""
import os
import logging
from typing import Optional

logger = logging.getLogger("EnOrdenWhatsApp")

_http_client = None


def _get_client():
    global _http_client
    if _http_client is None:
        import httpx
        _http_client = httpx.Client(timeout=15)
    return _http_client


def _get_config() -> tuple:
    token = os.getenv("WA_API_TOKEN", "").strip()
    phone_id = os.getenv("WA_PHONE_NUMBER_ID", "").strip()
    version = os.getenv("WA_API_VERSION", "v21.0").strip()
    return token, phone_id, version


def _format_phone(telefono: str) -> Optional[str]:
    if not telefono:
        return None
    digits = "".join(c for c in telefono if c.isdigit())
    if len(digits) == 10:
        return f"57{digits}"
    if len(digits) == 12 and digits.startswith("57"):
        return digits
    if len(digits) == 11 and digits.startswith("0"):
        return f"57{digits[1:]}"
    return None


def enviar_mensaje(telefono: str, mensaje: str) -> dict:
    token, phone_id, version = _get_config()
    if not token or not phone_id:
        logger.info(f"[WA no configurado] Mensaje no enviado a {telefono}: {mensaje[:60]}...")
        return {"success": False, "error": "WhatsApp no configurado (WA_API_TOKEN / WA_PHONE_NUMBER_ID)"}

    to = _format_phone(telefono)
    if not to:
        logger.warning(f"Teléfono inválido para WhatsApp: {telefono}")
        return {"success": False, "error": f"Teléfono inválido: {telefono}"}

    url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": mensaje},
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        client = _get_client()
        resp = client.post(url, json=payload, headers=headers)
        data = resp.json()
        if resp.status_code in (200, 201):
            msg_id = data.get("messages", [{}])[0].get("id", "")
            logger.info(f"WhatsApp enviado a {to} (id={msg_id})")
            return {"success": True, "wa_message_id": msg_id}
        else:
            logger.error(f"Error WhatsApp API {resp.status_code}: {data}")
            return {"success": False, "error": str(data)}
    except Exception as e:
        logger.error(f"Excepción enviando WhatsApp: {e}")
        return {"success": False, "error": str(e)}


def notificar_devolucion_cliente(cliente_nombre: str, telefono: str, descripcion: str, monto: float, tienda: str = "EnOrden") -> dict:
    mensaje = (
        f"🔄 *DEVOLUCIÓN REGISTRADA* - {tienda}\n\n"
        f"Hola {cliente_nombre},\n\n"
        f"Se ha registrado una devolución por:\n"
        f"📝 *{descripcion}*\n"
        f"💰 Monto: ${monto:,.2f}\n\n"
        f"Gracias por tu preferencia."
    )
    return enviar_mensaje(telefono, mensaje)


def notificar_devolucion_proveedor(proveedor_nombre: str, telefono: str, descripcion: str, monto: float, tienda: str = "EnOrden") -> dict:
    mensaje = (
        f"🔄 *DEVOLUCIÓN A PROVEEDOR* - {tienda}\n\n"
        f"Hola {proveedor_nombre},\n\n"
        f"Se ha registrado una devolución:\n"
        f"📝 *{descripcion}*\n"
        f"💰 Monto: ${monto:,.2f}\n\n"
        f"Quedamos atentos a cualquier novedad."
    )
    return enviar_mensaje(telefono, mensaje)
