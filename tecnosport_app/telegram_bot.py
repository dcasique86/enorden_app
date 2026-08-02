#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
EnOrden ERP - Bot de Telegram Administrativo
Permite consultar saldos de clientes y proveedores de forma segura desde la base de datos SQLite.
Usa el patrón repositorio existente en EnOrden.
"""

import os
import sys
import logging
from functools import wraps
from decimal import Decimal
from typing import Any, Optional

# Cargar variables de entorno desde el archivo .env
from dotenv import load_dotenv
load_dotenv()

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("EnOrdenTelegramBot")

# Intentar importar la librería python-telegram-bot
try:
    from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler
    TELEGRAM_LIB_OK = True
except ImportError:
    TELEGRAM_LIB_OK = False
    logger.warning("Librería 'python-telegram-bot' no instalada. El bot de Telegram no estará disponible.")
    logger.warning("Para instalarlo: pip install python-telegram-bot")

# Importar repositorios y base de datos de EnOrden
try:
    from repository import cliente_repo, proveedor_repo, telegram_user_repo
    from database import db
    from schemas import TelegramUserCreate
except ImportError:
    # Agregar el directorio actual al path en caso de ejecutarse desde fuera de su carpeta
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from repository import cliente_repo, proveedor_repo, telegram_user_repo
    from database import db
    from schemas import TelegramUserCreate

# Importaciones para FSM y API calls
try:
    import httpx
    HTTPX_OK = True
except ImportError:
    HTTPX_OK = False
    logger.warning("Librería 'httpx' no instalada. El bot de Telegram no estará disponible.")

from datetime import datetime
from uuid import uuid4



# Leer y validar credenciales de variables de entorno
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ADMIN_ID_RAW = os.getenv("TELEGRAM_ADMIN_ID")
TELEGRAM_ADMIN_ID = None

_application = None
_bot_thread = None
_bot_running = False


def validar_configuracion() -> dict:
    """Valida que la configuración del bot sea correcta.
    Retorna {'ok': bool, 'mensaje': str, 'codigo': str}.
    """
    if not TELEGRAM_LIB_OK:
        return {"ok": False, "mensaje": "python-telegram-bot no instalado", "codigo": "LIB_MISSING"}
    if not HTTPX_OK:
        return {"ok": False, "mensaje": "httpx no instalado", "codigo": "HTTPX_MISSING"}
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN in ("your_telegram_bot_token_here", "TU_TELEGRAM_BOT_TOKEN_AQUI"):
        return {"ok": False, "mensaje": "TELEGRAM_BOT_TOKEN no configurado en .env", "codigo": "TOKEN_MISSING"}
    if not TELEGRAM_ADMIN_ID_RAW or TELEGRAM_ADMIN_ID_RAW in ("your_telegram_admin_id_here", "TU_TELEGRAM_ID_AQUI"):
        return {"ok": False, "mensaje": "TELEGRAM_ADMIN_ID no configurado en .env", "codigo": "ADMIN_MISSING"}
    global TELEGRAM_ADMIN_ID
    try:
        TELEGRAM_ADMIN_ID = int(TELEGRAM_ADMIN_ID_RAW)
    except ValueError:
        return {"ok": False, "mensaje": f"TELEGRAM_ADMIN_ID '{TELEGRAM_ADMIN_ID_RAW}' no es un número válido", "codigo": "ADMIN_INVALID"}
    return {"ok": True, "mensaje": "Configuración válida", "codigo": "OK", "admin_id": TELEGRAM_ADMIN_ID}

# ==================== HELPERS ====================

def format_currency(val: Any) -> str:
    """Formatea valores numéricos a formato de moneda con punto como separador de miles.
    Ej: 150000 -> $150.000
    """
    try:
        if val is None:
            return "$0"
        num = float(val)
        return f"${int(num):,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(val)

def _format_cliente_detalle(c) -> str:
    """Formatea la información detallada de un cliente incluyendo el último abono."""
    estado = "🟢 Activo" if c.activo else "🔴 Inactivo"
    dias_sin_abono = f"{c.dias_sin_abonar} días" if c.dias_sin_abonar is not None else "Sin abonos registrados"

    # Obtener el último abono usando la consulta existente get_movimientos_by_cliente
    try:
        movimientos = db.get_movimientos_by_cliente(str(c.id))
        abonos = [m for m in movimientos if m.get('tipo') == 'abono']
    except Exception:
        abonos = []

    if abonos:
        u = abonos[0]
        fecha_mov = u.get('fecha', 'N/A')
        monto_mov = format_currency(u.get('monto', 0))
        desc_raw = u.get('descripcion', '')
        desc_val = desc_raw.strip() if isinstance(desc_raw, str) else ""
        desc_line = f"\n📝 *Descripción:* {desc_val}" if desc_val else ""

        mov_info = (
            f"📅 *Fecha:* {fecha_mov}\n"
            f"💵 *Monto:* {monto_mov}"
            f"{desc_line}"
        )
    else:
        mov_info = "Sin movimientos registrados."

    return (
        f"👤 *Detalle del Cliente*\n"
        f"===========================\n"
        f"📛 *Nombre:* {c.nombre}\n"
        f"📞 *Teléfono:* {c.telefono or 'No registrado'}\n"
        f"📌 *Estado:* {estado}\n"
        f"---------------------------\n"
        f"💵 *Saldo Pendiente:* `{format_currency(c.saldo)}`\n"
        f"🤝 *Total Prestado:* {format_currency(c.total_prestado)}\n"
        f"📥 *Total Abonado:* {format_currency(c.total_abonado)}\n"
        f"📅 *Días sin Abonar:* {dias_sin_abono}\n"
        f"---------------------------\n"
        f"📥 *Último Abono:*\n{mov_info}\n"
        f"==========================="
    )

def _format_proveedor_detalle(p) -> str:
    """Formatea la información detallada de un proveedor incluyendo el último pago."""
    estado = "🟢 Activo" if p.activo else "🔴 Inactivo"

    # Obtener el último pago usando la consulta existente get_movimientos_by_proveedor
    try:
        movimientos = db.get_movimientos_by_proveedor(str(p.id))
        pagos = [m for m in movimientos if m.get('tipo') == 'pago']
    except Exception:
        pagos = []

    if pagos:
        u = pagos[0]
        fecha_mov = u.get('fecha', 'N/A')
        monto_mov = format_currency(u.get('monto', 0))
        desc_raw = u.get('descripcion', '')
        desc_val = desc_raw.strip() if isinstance(desc_raw, str) else ""
        desc_line = f"\n📝 *Descripción:* {desc_val}" if desc_val else ""

        mov_info = (
            f"📅 *Fecha:* {fecha_mov}\n"
            f"💸 *Monto:* {monto_mov}"
            f"{desc_line}"
        )
    else:
        mov_info = "Sin movimientos registrados."

    return (
        f"🏭 *Detalle del Proveedor*\n"
        f"===========================\n"
        f"📛 *Nombre:* {p.nombre}\n"
        f"📞 *Teléfono:* {p.telefono or 'No registrado'}\n"
        f"📌 *Estado:* {estado}\n"
        f"---------------------------\n"
        f"🧡 *Deuda Actual:* `{format_currency(p.saldo)}`\n"
        f"📄 *Total Facturas:* {format_currency(p.total_facturas)}\n"
        f"💸 *Total Pagado:* {format_currency(p.total_pagado)}\n"
        f"---------------------------\n"
        f"💸 *Último Pago:*\n{mov_info}\n"
        f"==========================="
    )

# ==================== SEGURIDAD ====================

ROLES = {
    "super_admin": 100,
    "admin": 50,
    "operador": 10,
}

def _get_user_role(telegram_id: int) -> Optional[str]:
    """Consulta el rol del usuario en la BD. Retorna None si no existe o está inactivo."""
    try:
        data = telegram_user_repo.get_by_telegram_id(telegram_id)
        if data and data["activo"]:
            return data["rol"]
    except Exception as e:
        logger.error(f"Error consultando rol para {telegram_id}: {e}")
    return None

def role_required(*allowed_roles: str):
    """Decorador que restringe el acceso según el rol del usuario almacenado en BD."""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user = update.effective_user
            if not user:
                logger.warning("Comando recibido sin datos de usuario.")
                return

            role = _get_user_role(user.id)
            if not role:
                logger.warning(f"Acceso denegado para usuario ID: {user.id} — no registrado o inactivo")
                if update.message:
                    await update.message.reply_text(
                        "❌ *Acceso denegado.*\n"
                        "No tienes permisos para usar este bot.",
                        parse_mode="Markdown"
                    )
                return

            if role not in allowed_roles:
                logger.warning(f"Permiso denegado para {user.id} (rol={role}), requiere: {allowed_roles}")
                if update.message:
                    await update.message.reply_text(
                        "❌ *Acceso denegado.*\n"
                        "No tienes permiso para ejecutar esta acción con tu rol actual.",
                        parse_mode="Markdown"
                    )
                return

            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

# ==================== HANDLERS DE COMANDOS ====================

# Teclado de navegación principal (se construye una sola vez al cargar el módulo)
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("📥 Abono"), KeyboardButton("📤 Préstamo"), KeyboardButton("🧾 Gasto")],
        [KeyboardButton("🔍 Buscar"), KeyboardButton("👥 Clientes"), KeyboardButton("🏢 Proveedores")],
        [KeyboardButton("💰 Caja"), KeyboardButton("📊 Reportes")],
    ],
    resize_keyboard=True,
)


def _build_resumen_inicio() -> str:
    """Construye el texto del resumen de pantalla de inicio.
    Reutiliza: cliente_repo.get_con_deuda(), proveedor_repo.get_all() y
    db.obtener_resumen_caja_diaria(). No ejecuta consultas SQL adicionales.
    """
    from datetime import datetime

    # ── Clientes con saldo pendiente ──────────────────────────────────────────
    try:
        clientes_con_deuda = cliente_repo.get_con_deuda()
        total_clientes_deuda = len(clientes_con_deuda)
        monto_clientes = sum(c.saldo for c in clientes_con_deuda)
    except Exception:
        total_clientes_deuda = 0
        monto_clientes = Decimal("0")

    # ── Proveedores con deuda pendiente ───────────────────────────────────────
    try:
        todos_proveedores = proveedor_repo.get_all()
        proveedores_con_deuda = [p for p in todos_proveedores if p.saldo > Decimal("0")]
        total_proveedores_deuda = len(proveedores_con_deuda)
        monto_proveedores = sum(p.saldo for p in proveedores_con_deuda)
    except Exception:
        total_proveedores_deuda = 0
        monto_proveedores = Decimal("0")

    # ── Caja del día (reutiliza función existente sin SQL extra) ──────────────
    try:
        caja = db.obtener_resumen_caja_diaria()  # Sin argumento → usa fecha de hoy
        ventas_hoy = caja.get("ventas_total", 0.0)
        abonos_hoy = caja.get("abonos_total", 0.0)
        pagos_prov_hoy = caja.get("pagos_proveedores_total", 0.0)
        gastos_hoy = caja.get("gastos_total", 0.0)
        efectivo_neto = caja.get("efectivo_neto", 0.0)
    except Exception:
        ventas_hoy = abonos_hoy = pagos_prov_hoy = gastos_hoy = efectivo_neto = 0.0

    # ── Fecha y hora actuales ─────────────────────────────────────────────────
    ahora = datetime.now().strftime("%d/%m/%Y  %H:%M")

    texto = (
        f"🤖 *EnOrden ERP — Panel Administrativo*\n"
        f"🟢 Conexión activa con la base de datos\n"
        f"🕐 `{ahora}`\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 *CLIENTES CON SALDO PENDIENTE*\n"
        f"   Cantidad: *{total_clientes_deuda}* clientes\n"
        f"   Total por cobrar: `{format_currency(monto_clientes)}`\n"
        f"\n"
        f"🏢 *PROVEEDORES CON DEUDA*\n"
        f"   Cantidad: *{total_proveedores_deuda}* proveedores\n"
        f"   Total por pagar: `{format_currency(monto_proveedores)}`\n"
        f"\n"
        f"💰 *CAJA DEL DÍA*\n"
        f"   💵 Ventas en efectivo: `{format_currency(ventas_hoy)}`\n"
        f"   📥 Abonos recibidos:   `{format_currency(abonos_hoy)}`\n"
        f"   📤 Pagos proveedores:  `{format_currency(pagos_prov_hoy)}`\n"
        f"   🧾 Gastos operativos:  `{format_currency(gastos_hoy)}`\n"
        f"   ─────────────────────────────\n"
        f"   🏦 Efectivo neto: `{format_currency(efectivo_neto)}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"💡 *Instrucciones rápidas:*\n"
        f"  • Usa *🔍 Buscar* o escribe un nombre para consultar clientes o proveedores.\n"
        f"  • Toca cualquier botón del menú inferior para navegar."
    )
    return texto


@role_required("super_admin", "admin", "operador")
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start: Muestra el resumen del día y el teclado de navegación."""
    await update.message.reply_chat_action(action="typing")
    texto = _build_resumen_inicio()
    await update.message.reply_text(
        texto,
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )

@role_required("super_admin", "admin", "operador")
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help: Muestra la pantalla de inicio con resumen y teclado."""
    await start_command(update, context)


async def keyboard_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los botones del teclado de navegación principal y búsquedas interactivas.
    Cada botón responde con el resumen o instrucción correspondiente.
    Valida permisos según el rol del usuario.
    """
    user = update.effective_user
    if not user:
        return
    role = _get_user_role(user.id)
    if not role:
        await update.message.reply_text(
            "❌ *Acceso denegado.*\nNo tienes permisos para usar este bot.",
            parse_mode="Markdown"
        )
        return

    texto_boton = update.message.text.strip()
    await update.message.reply_chat_action(action="typing")

    if texto_boton == "🔍 Buscar":
        if role not in ("super_admin", "admin", "operador"):
            await update.message.reply_text("❌ No tienes permiso para esta acción.", reply_markup=MAIN_KEYBOARD)
            return
        context.user_data['esperando_busqueda'] = True
        await update.message.reply_text(
            "🔍 *Búsqueda de Clientes y Proveedores*\n\n"
            "Escribe un nombre o teléfono.",
            parse_mode="Markdown",
            reply_markup=MAIN_KEYBOARD,
        )

    elif texto_boton == "👥 Clientes":
        if role not in ("super_admin", "admin", "operador"):
            await update.message.reply_text("❌ No tienes permiso para esta acción.", reply_markup=MAIN_KEYBOARD)
            return
        context.user_data['esperando_busqueda'] = False
        try:
            clientes_deuda = cliente_repo.get_con_deuda()
            if not clientes_deuda:
                await update.message.reply_text(
                    "✅ *Clientes* — No hay clientes con saldo pendiente.",
                    parse_mode="Markdown",
                    reply_markup=MAIN_KEYBOARD,
                )
                return
            lineas = [f"👥 *Clientes con saldo pendiente ({len(clientes_deuda)}):*\n"]
            for c in clientes_deuda[:15]:
                lineas.append(f"• {c.nombre}: `{format_currency(c.saldo)}`")
            if len(clientes_deuda) > 15:
                lineas.append(f"_...y {len(clientes_deuda) - 15} más._")
            lineas.append("\n💡 Toca *🔍 Buscar* y escribe el nombre del cliente para ver su detalle.")
            await update.message.reply_text(
                "\n".join(lineas),
                parse_mode="Markdown",
                reply_markup=MAIN_KEYBOARD,
            )
        except Exception as e:
            logger.error(f"Error en botón Clientes: {e}", exc_info=True)
            await update.message.reply_text("❌ Error al cargar clientes.", reply_markup=MAIN_KEYBOARD)

    elif texto_boton == "🏢 Proveedores":
        if role not in ("super_admin", "admin"):
            await update.message.reply_text("❌ No tienes permiso para esta acción.", reply_markup=MAIN_KEYBOARD)
            return
        context.user_data['esperando_busqueda'] = False
        try:
            todos = proveedor_repo.get_all()
            proveedores_deuda = [p for p in todos if p.saldo > Decimal("0")]
            if not proveedores_deuda:
                await update.message.reply_text(
                    "✅ *Proveedores* — No hay deudas pendientes con proveedores.",
                    parse_mode="Markdown",
                    reply_markup=MAIN_KEYBOARD,
                )
                return
            lineas = [f"🏢 *Proveedores con deuda ({len(proveedores_deuda)}):*\n"]
            for p in proveedores_deuda[:15]:
                lineas.append(f"• {p.nombre}: `{format_currency(p.saldo)}`")
            if len(proveedores_deuda) > 15:
                lineas.append(f"_...y {len(proveedores_deuda) - 15} más._")
            lineas.append("\n💡 Toca *🔍 Buscar* y escribe el nombre del proveedor para ver su detalle.")
            await update.message.reply_text(
                "\n".join(lineas),
                parse_mode="Markdown",
                reply_markup=MAIN_KEYBOARD,
            )
        except Exception as e:
            logger.error(f"Error en botón Proveedores: {e}", exc_info=True)
            await update.message.reply_text("❌ Error al cargar proveedores.", reply_markup=MAIN_KEYBOARD)

    elif texto_boton == "💰 Caja":
        if role not in ("super_admin", "admin"):
            await update.message.reply_text("❌ No tienes permiso para esta acción.", reply_markup=MAIN_KEYBOARD)
            return
        context.user_data['esperando_busqueda'] = False
        try:
            caja = db.obtener_resumen_caja_diaria()
            from datetime import datetime
            fecha = datetime.now().strftime("%d/%m/%Y")
            texto = (
                f"💰 *Caja del día — {fecha}*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💵 Ventas en efectivo: `{format_currency(caja.get('ventas_total', 0))}`\n"
                f"📥 Abonos recibidos:   `{format_currency(caja.get('abonos_total', 0))}`\n"
                f"📤 Pagos proveedores:  `{format_currency(caja.get('pagos_proveedores_total', 0))}`\n"
                f"🧾 Gastos operativos:  `{format_currency(caja.get('gastos_total', 0))}`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🏦 *Efectivo neto: `{format_currency(caja.get('efectivo_neto', 0))}`*"
            )
            await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=MAIN_KEYBOARD)
        except Exception as e:
            logger.error(f"Error en botón Caja: {e}", exc_info=True)
            await update.message.reply_text("❌ Error al obtener resumen de caja.", reply_markup=MAIN_KEYBOARD)

    elif texto_boton == "📊 Reportes":
        if role not in ("super_admin", "admin"):
            await update.message.reply_text("❌ No tienes permiso para esta acción.", reply_markup=MAIN_KEYBOARD)
            return
        context.user_data['esperando_busqueda'] = False
        await update.message.reply_text(
            "📊 *Opciones de consulta:*\n\n"
            "  🔍 *Buscar* — Escribe el nombre o teléfono de cualquier cliente o proveedor.\n"
            "  👥 *Clientes* — Ver lista de clientes con saldo pendiente.\n"
            "  🏢 *Proveedores* — Ver lista de proveedores con deuda.\n"
            "  💰 *Caja* — Ver resumen del flujo de caja del día.",
            parse_mode="Markdown",
            reply_markup=MAIN_KEYBOARD,
        )

    elif context.user_data.get('esperando_busqueda'):
        context.user_data['esperando_busqueda'] = False
        query = texto_boton
        try:
            clientes = cliente_repo.buscar(query)
            proveedores = proveedor_repo.buscar(query)
            total = len(clientes) + len(proveedores)

            if total == 0:
                await update.message.reply_text(
                    f"❌ No se encontraron clientes ni proveedores que coincidan con *\"{query}\"*.",
                    parse_mode="Markdown",
                    reply_markup=MAIN_KEYBOARD,
                )
            elif total == 1:
                if len(clientes) == 1:
                    mensaje = _format_cliente_detalle(clientes[0])
                else:
                    mensaje = _format_proveedor_detalle(proveedores[0])
                await update.message.reply_text(
                    mensaje,
                    parse_mode="Markdown",
                    reply_markup=MAIN_KEYBOARD,
                )
            else:
                lineas = [f"🔍 *Resultados de búsqueda para \"{query}\" ({total}):*\n"]
                if clientes:
                    lineas.append(f"👥 *Clientes ({len(clientes)}):*")
                    for idx, c in enumerate(clientes[:10], 1):
                        lineas.append(f"{idx}. *{c.nombre}* - Saldo: `{format_currency(c.saldo)}`")
                    if len(clientes) > 10:
                        lineas.append(f"_...y {len(clientes) - 10} clientes más._")
                    lineas.append("")
                if proveedores:
                    lineas.append(f"🏢 *Proveedores ({len(proveedores)}):*")
                    for idx, p in enumerate(proveedores[:10], 1):
                        lineas.append(f"{idx}. *{p.nombre}* - Deuda: `{format_currency(p.saldo)}`")
                    if len(proveedores) > 10:
                        lineas.append(f"_...y {len(proveedores) - 10} proveedores más._")
                lineas.append("\n💡 Escribe el nombre completo o más específico para ver el detalle.")

                await update.message.reply_text(
                    "\n".join(lineas),
                    parse_mode="Markdown",
                    reply_markup=MAIN_KEYBOARD,
                )
        except Exception as e:
            logger.error(f"Error al realizar búsqueda unificada '{query}': {e}", exc_info=True)
            await update.message.reply_text(
                "❌ *Error interno al realizar la búsqueda.*",
                parse_mode="Markdown",
                reply_markup=MAIN_KEYBOARD,
            )

    else:
        # Texto no reconocido o mensaje normal
        pass

@role_required("super_admin", "admin", "operador")
async def saldo_cliente_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /saldo_cliente <nombre o apellido>: Busca clientes y muestra su saldo."""
    if not context.args:
        await update.message.reply_text(
            "🔍 *Consulta de Cliente*\n"
            "Escribe el nombre del cliente o usa *🔍 Buscar* para ver el detalle.\n"
            "Ejemplo: `denis`",
            parse_mode="Markdown"
        )
        return

    query = " ".join(context.args).strip()
    await update.message.reply_chat_action(action="typing")

    try:
        # Buscar clientes en el repositorio
        clientes = cliente_repo.buscar(query)

        if not clientes:
            await update.message.reply_text(
                f"👤 Cliente *\"{query}\"* no encontrado en la base de datos.",
                parse_mode="Markdown"
            )
            return

        if len(clientes) == 1:
            # Un solo resultado encontrado: Mostrar reporte detallado usando helper centralizado
            mensaje = _format_cliente_detalle(clientes[0])
            await update.message.reply_text(mensaje, parse_mode="Markdown")
        else:
            # Múltiples coincidencias encontradas: Listar coincidencias
            lista_clientes = []
            for idx, c in enumerate(clientes[:15], 1):
                lista_clientes.append(f"{idx}. *{c.nombre}* - Saldo: `{format_currency(c.saldo)}`")
            
            opciones_str = "\n".join(lista_clientes)
            total_coincidencias = len(clientes)
            exceso_str = f"\n_...y {total_coincidencias - 15} clientes más._" if total_coincidencias > 15 else ""

            mensaje = (
                f"🔍 *Múltiples clientes encontrados ({total_coincidencias}):*\n"
                f"Por favor, sé más específico con el nombre.\n\n"
                f"{opciones_str}{exceso_str}\n\n"
                f"💡 _Vuelve a buscar ingresando más caracteres o el nombre completo._"
            )
            await update.message.reply_text(mensaje, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error al consultar saldo de cliente '{query}': {e}", exc_info=True)
        await update.message.reply_text(
            "❌ *Error interno de base de datos.*\n"
            "No se pudo completar la consulta de cliente en este momento.",
            parse_mode="Markdown"
        )

@role_required("super_admin", "admin")
async def saldo_proveedor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /saldo_proveedor <nombre o apellido>: Busca proveedores y muestra la deuda."""
    if not context.args:
        await update.message.reply_text(
            "🔍 *Consulta de Proveedor*\n"
            "Escribe el nombre del proveedor o usa *🔍 Buscar* para ver el detalle.\n"
            "Ejemplo: `distribuidora`",
            parse_mode="Markdown"
        )
        return

    query = " ".join(context.args).strip()
    await update.message.reply_chat_action(action="typing")

    try:
        # Buscar proveedores en el repositorio
        proveedores = proveedor_repo.buscar(query)

        if not proveedores:
            await update.message.reply_text(
                f"🏭 Proveedor *\"{query}\"* no encontrado en la base de datos.",
                parse_mode="Markdown"
            )
            return

        if len(proveedores) == 1:
            # Un solo resultado encontrado: Mostrar reporte detallado usando helper centralizado
            mensaje = _format_proveedor_detalle(proveedores[0])
            await update.message.reply_text(mensaje, parse_mode="Markdown")
        else:
            # Múltiples coincidencias encontradas: Listar coincidencias
            lista_proveedores = []
            for idx, p in enumerate(proveedores[:15], 1):
                lista_proveedores.append(f"{idx}. *{p.nombre}* - Deuda: `{format_currency(p.saldo)}`")
            
            opciones_str = "\n".join(lista_proveedores)
            total_coincidencias = len(proveedores)
            exceso_str = f"\n_...y {total_coincidencias - 15} proveedores más._" if total_coincidencias > 15 else ""

            mensaje = (
                f"🔍 *Múltiples proveedores encontrados ({total_coincidencias}):*\n"
                f"Por favor, sé más específico con el nombre.\n\n"
                f"{opciones_str}{exceso_str}\n\n"
                f"💡 _Vuelve a buscar ingresando más caracteres o el nombre completo._"
            )
            await update.message.reply_text(mensaje, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error al consultar saldo de proveedor '{query}': {e}", exc_info=True)
        await update.message.reply_text(
            "❌ *Error interno de base de datos.*\n"
            "No se pudo completar la consulta de proveedor en este momento.",
            parse_mode="Markdown"
        )

# ==================== FSM: CONSTANTES Y HELPERS ====================

# Estados para las conversaciones
ABONO_BUSCAR, ABONO_SEL, ABONO_MONTO, ABONO_DESC, ABONO_CONF = range(5)
PRESTAMO_BUSCAR, PRESTAMO_SEL, PRESTAMO_MONTO, PRESTAMO_DESC, PRESTAMO_CONF = range(5, 10)
GASTO_CATEGORIA, GASTO_MONTO, GASTO_DESC, GASTO_CONF = range(10, 14)

# Timeout de conversacion: 5 minutos
CONV_TIMEOUT = 300

# Cliente HTTP compartido para llamadas a la API local
API_BASE = "http://127.0.0.1:8000"
_http_client = None

async def _get_http_client():
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(base_url=API_BASE, timeout=10.0)
    return _http_client

async def _call_api(method: str, path: str, json_data: dict = None):
    """Llama a un endpoint FastAPI local y retorna el JSON de respuesta."""
    client = await _get_http_client()
    try:
        resp = await client.request(method, path, json=json_data)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        detail = "Error del servidor"
        try:
            detail = e.response.json().get("detail", detail)
        except Exception:
            pass
        raise ValueError(detail)
    except httpx.RequestError as e:
        raise ValueError(f"Error de conexion con la API: {e}")

def _build_cliente_keyboard(clientes, prefix: str):
    """Construye un teclado inline con clientes para seleccion."""
    keyboard = []
    for c in clientes[:10]:
        keyboard.append([InlineKeyboardButton(
            f"{c.nombre} - Saldo: ${c.saldo:,.0f}".replace(",", "."),
            callback_data=f"{prefix}_sel:{c.id}"
        )])
    if len(clientes) > 10:
        keyboard.append([InlineKeyboardButton(
            f"Subio {len(clientes) - 10} mas - se mas especifico",
            callback_data=f"{prefix}_more"
        )])
    return InlineKeyboardMarkup(keyboard)

def _build_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Si, confirmar", callback_data="confirm_yes")],
        [InlineKeyboardButton("Cancelar", callback_data="confirm_no")]
    ])

def _build_cancel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Cancelar operacion", callback_data="cancel_op")]
    ])

async def _send_typing(update: Update):
    await update.message.reply_chat_action(action="typing")

async def cancelar_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela cualquier operacion en curso via /cancelar."""
    context.user_data.clear()
    await update.message.reply_text(
        "Operacion cancelada.\n"
        "Usa /start para volver al menu principal.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def cancelar_operation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela via boton inline."""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("Operacion cancelada.")
    return ConversationHandler.END

async def timeout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Timeout de conversacion - 5 minutos."""
    context.user_data.clear()
    await update.message.reply_text(
        "Tiempo de espera agotado.\n"
        "La operacion se ha cancelado por inactividad.\n"
        "Usa /start para volver al menu principal.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

@role_required("super_admin", "admin")
async def cliente_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /cliente - Busca un cliente y muestra su detalle completo."""
    await _send_typing(update)
    msg_parts = update.message.text.split(maxsplit=1)
    if len(msg_parts) < 2:
        await update.message.reply_text(
            "Consulta de Cliente\n\n"
            "Escribe el nombre del cliente:\n"
            "Ejemplo: /cliente denis",
            parse_mode="Markdown"
        )
        return

    query = msg_parts[1].strip()
    try:
        clientes = cliente_repo.buscar(query)
        if not clientes:
            await update.message.reply_text(
                f"No se encontraron clientes para \"{query}\".",
                parse_mode="Markdown"
            )
            return

        if len(clientes) == 1:
            await update.message.reply_text(
                _format_cliente_detalle(clientes[0]),
                parse_mode="Markdown"
            )
        else:
            lineas = [f"Varios clientes encontrados ({len(clientes)}):\n"]
            for idx, c in enumerate(clientes[:15], 1):
                lineas.append(f"{idx}. {c.nombre} - Saldo: `{format_currency(c.saldo)}`")
            if len(clientes) > 15:
                lineas.append(f"_...y {len(clientes) - 15} mas._")
            lineas.append("\nUsa /cliente nombre completo para ver el detalle.")
            await update.message.reply_text("\n".join(lineas), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error en /cliente: {e}", exc_info=True)
        await update.message.reply_text("Error al consultar cliente.", parse_mode="Markdown")

# ==================== FSM: ABONO ====================

@role_required("super_admin", "admin", "operador")
async def abono_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo de registro de abono."""
    context.user_data.clear()
    await update.message.reply_text(
        "Registro de Abono - Paso 1/4\n\n"
        "Escribe el nombre o telefono del cliente:",
        parse_mode="Markdown",
        reply_markup=_build_cancel_keyboard()
    )
    return ABONO_BUSCAR

async def abono_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Busca clientes por nombre y muestra resultados para seleccionar."""
    query = update.message.text.strip()
    cancel_btn = _build_cancel_keyboard()
    try:
        clientes = cliente_repo.buscar(query)
        if not clientes:
            await update.message.reply_text(
                f"No se encontro ningun cliente para \"{query}\".\n\n"
                "Escribe otro nombre o usa /cancelar para salir.",
                parse_mode="Markdown",
                reply_markup=cancel_btn
            )
            return ABONO_BUSCAR

        keyboard = _build_cliente_keyboard(clientes, "abono")
        await update.message.reply_text(
            f"{len(clientes)} cliente(s) encontrado(s). Selecciona uno:",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        context.user_data['resultados'] = {str(c.id): c for c in clientes}
        return ABONO_SEL
    except Exception as e:
        logger.error(f"Error buscando clientes: {e}", exc_info=True)
        await update.message.reply_text("Error buscando clientes.", reply_markup=cancel_btn)
        return ABONO_BUSCAR

async def abono_seleccionar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback cuando el usuario selecciona un cliente de la lista."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "abono_more":
        cancel_btn = _build_cancel_keyboard()
        await query.edit_message_text(
            "Escribe un nombre mas especifico para encontrar al cliente:",
            reply_markup=cancel_btn
        )
        return ABONO_BUSCAR

    cliente_id = data.split(":")[1]
    resultados = context.user_data.get('resultados', {})
    cliente = resultados.get(cliente_id)
    if not cliente:
        try:
            c_data = db.get_cliente_by_id(cliente_id)
            from collections import namedtuple
            ClienteTuple = namedtuple("Cliente", ["id", "nombre", "saldo", "telefono", "activo", "total_prestado", "total_abonado", "dias_sin_abonar"])
            cliente = ClienteTuple(
                id=c_data['id'], nombre=c_data['nombre'], saldo=c_data.get('saldo', 0),
                telefono=c_data.get('telefono', ''), activo=c_data.get('activo', True),
                total_prestado=c_data.get('total_prestado', 0),
                total_abonado=c_data.get('total_abonado', 0),
                dias_sin_abonar=c_data.get('dias_sin_abonar', 0)
            )
        except Exception as e:
            logger.error(f"Error obteniendo cliente: {e}")
            await query.edit_message_text("Cliente no encontrado.")
            return ConversationHandler.END

    context.user_data['cliente'] = cliente
    context.user_data['cliente_id'] = cliente.id
    await query.edit_message_text(
        f"Abono - Paso 2/4\n\n"
        f"Cliente: {cliente.nombre}\n"
        f"Saldo actual: `{format_currency(cliente.saldo)}`\n\n"
        f"Cual es el monto del abono?",
        parse_mode="Markdown",
        reply_markup=_build_cancel_keyboard()
    )
    return ABONO_MONTO

async def abono_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el monto del abono."""
    text = update.message.text.strip()
    cancel_btn = _build_cancel_keyboard()
    try:
        monto = float(text.replace("$", "").replace(".", "").replace(",", ".").strip())
        if monto <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "Monto invalido. Ingresa un numero valido mayor a 0.\nEjemplo: 50000",
            parse_mode="Markdown",
            reply_markup=cancel_btn
        )
        return ABONO_MONTO

    context.user_data['monto'] = monto
    cliente = context.user_data['cliente']
    await update.message.reply_text(
        f"Abono - Paso 3/4\n\n"
        f"Cliente: {cliente.nombre}\n"
        f"Monto: `{format_currency(monto)}`\n\n"
        f"Descripcion (opcional):\n"
        f"Escribe una descripcion o un guion (-) para omitir:",
        parse_mode="Markdown",
        reply_markup=_build_cancel_keyboard()
    )
    return ABONO_DESC

async def abono_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la descripcion del abono y muestra resumen para confirmar."""
    desc = update.message.text.strip()
    if desc == "-":
        desc = ""

    context.user_data['descripcion'] = desc
    cliente = context.user_data['cliente']
    monto = context.user_data['monto']
    saldo_nuevo = float(cliente.saldo) - monto

    texto = (
        f"Resumen del Abono\n"
        f"-----------------------\n"
        f"Cliente: {cliente.nombre}\n"
        f"Monto: `{format_currency(monto)}`\n"
        f"Descripcion: {desc or '-'}\n"
        f"-----------------------\n"
        f"Saldo anterior: `{format_currency(float(cliente.saldo))}`\n"
        f"Saldo restante: `{format_currency(saldo_nuevo)}`\n"
        f"-----------------------\n"
        f"Confirmar el registro?"
    )
    await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=_build_confirm_keyboard())
    return ABONO_CONF

async def abono_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback de confirmacion - ejecuta el abono via API."""
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_no":
        context.user_data.clear()
        await query.edit_message_text("Operacion cancelada.")
        return ConversationHandler.END

    cliente = context.user_data['cliente']
    monto = context.user_data['monto']
    descripcion = context.user_data.get('descripcion', '')

    await query.edit_message_text("Registrando abono...")

    try:
        result = await _call_api("POST", "/api/movimientos", {
            "cliente_id": str(cliente.id),
            "tipo": "abono",
            "monto": monto,
            "descripcion": descripcion or "Abono registrado por Telegram"
        })
        data = result.get("data", result)
        resumen = db.get_resumen_cliente(str(cliente.id))
        saldo_nuevo = resumen.get("saldo", float(cliente.saldo) - monto)

        comprobante = (
            f"ABONO REGISTRADO EXITOSAMENTE\n"
            f"-----------------------\n"
            f"Recibo #: `{data.get('id', '-')[:8]}...`\n"
            f"Cliente: {cliente.nombre}\n"
            f"Valor abonado: `{format_currency(monto)}`\n"
            f"Descripcion: {descripcion or '-'}\n"
            f"-----------------------\n"
            f"Saldo anterior: `{format_currency(float(cliente.saldo))}`\n"
            f"Saldo actual: `{format_currency(saldo_nuevo)}`\n"
            f"-----------------------\n"
            f"{datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            f"-----------------------\n"
            f"/start - Menu principal"
        )
        await query.edit_message_text(comprobante, parse_mode="Markdown")
    except ValueError as e:
        await query.edit_message_text(f"Error al registrar abono:\n{str(e)}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error registrando abono: {e}", exc_info=True)
        await query.edit_message_text("Error inesperado al registrar el abono.")

    context.user_data.clear()
    return ConversationHandler.END

# ==================== FSM: PRESTAMO ====================

@role_required("super_admin", "admin", "operador")
async def prestamo_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo de registro de prestamo."""
    context.user_data.clear()
    await update.message.reply_text(
        "Registro de Prestamo - Paso 1/4\n\n"
        "Escribe el nombre o telefono del cliente:",
        parse_mode="Markdown",
        reply_markup=_build_cancel_keyboard()
    )
    return PRESTAMO_BUSCAR

async def prestamo_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Busca clientes por nombre para prestamo."""
    query = update.message.text.strip()
    cancel_btn = _build_cancel_keyboard()
    try:
        clientes = cliente_repo.buscar(query)
        if not clientes:
            await update.message.reply_text(
                f"No se encontro ningun cliente para \"{query}\".\n\n"
                "Escribe otro nombre o usa /cancelar para salir.",
                parse_mode="Markdown",
                reply_markup=cancel_btn
            )
            return PRESTAMO_BUSCAR

        keyboard = _build_cliente_keyboard(clientes, "prestamo")
        await update.message.reply_text(
            f"{len(clientes)} cliente(s) encontrado(s). Selecciona uno:",
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        context.user_data['resultados'] = {str(c.id): c for c in clientes}
        return PRESTAMO_SEL
    except Exception as e:
        logger.error(f"Error buscando clientes: {e}", exc_info=True)
        await update.message.reply_text("Error buscando clientes.", reply_markup=cancel_btn)
        return PRESTAMO_BUSCAR

async def prestamo_seleccionar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback cuando el usuario selecciona un cliente para prestamo."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "prestamo_more":
        cancel_btn = _build_cancel_keyboard()
        await query.edit_message_text(
            "Escribe un nombre mas especifico para encontrar al cliente:",
            reply_markup=cancel_btn
        )
        return PRESTAMO_BUSCAR

    cliente_id = data.split(":")[1]
    resultados = context.user_data.get('resultados', {})
    cliente = resultados.get(cliente_id)
    if not cliente:
        try:
            c_data = db.get_cliente_by_id(cliente_id)
            from collections import namedtuple
            ClienteTuple = namedtuple("Cliente", ["id", "nombre", "saldo", "telefono", "activo", "total_prestado", "total_abonado", "dias_sin_abonar"])
            cliente = ClienteTuple(
                id=c_data['id'], nombre=c_data['nombre'], saldo=c_data.get('saldo', 0),
                telefono=c_data.get('telefono', ''), activo=c_data.get('activo', True),
                total_prestado=c_data.get('total_prestado', 0),
                total_abonado=c_data.get('total_abonado', 0),
                dias_sin_abonar=c_data.get('dias_sin_abonar', 0)
            )
        except Exception as e:
            logger.error(f"Error obteniendo cliente: {e}")
            await query.edit_message_text("Cliente no encontrado.")
            return ConversationHandler.END

    context.user_data['cliente'] = cliente
    context.user_data['cliente_id'] = cliente.id
    await query.edit_message_text(
        f"Prestamo - Paso 2/4\n\n"
        f"Cliente: {cliente.nombre}\n"
        f"Saldo actual: `{format_currency(cliente.saldo)}`\n\n"
        f"Cual es el monto del prestamo?",
        parse_mode="Markdown",
        reply_markup=_build_cancel_keyboard()
    )
    return PRESTAMO_MONTO

async def prestamo_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el monto del prestamo."""
    text = update.message.text.strip()
    cancel_btn = _build_cancel_keyboard()
    try:
        monto = float(text.replace("$", "").replace(".", "").replace(",", ".").strip())
        if monto <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "Monto invalido. Ingresa un numero valido mayor a 0.\nEjemplo: 100000",
            parse_mode="Markdown",
            reply_markup=cancel_btn
        )
        return PRESTAMO_MONTO

    context.user_data['monto'] = monto
    cliente = context.user_data['cliente']
    await update.message.reply_text(
        f"Prestamo - Paso 3/4\n\n"
        f"Cliente: {cliente.nombre}\n"
        f"Monto: `{format_currency(monto)}`\n\n"
        f"Descripcion (opcional):\n"
        f"Escribe una descripcion o un guion (-) para omitir:",
        parse_mode="Markdown",
        reply_markup=_build_cancel_keyboard()
    )
    return PRESTAMO_DESC

async def prestamo_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la descripcion y muestra resumen del prestamo."""
    desc = update.message.text.strip()
    if desc == "-":
        desc = ""

    context.user_data['descripcion'] = desc
    cliente = context.user_data['cliente']
    monto = context.user_data['monto']
    saldo_nuevo = float(cliente.saldo) + monto

    texto = (
        f"Resumen del Prestamo\n"
        f"-----------------------\n"
        f"Cliente: {cliente.nombre}\n"
        f"Monto: `{format_currency(monto)}`\n"
        f"Descripcion: {desc or '-'}\n"
        f"-----------------------\n"
        f"Saldo anterior: `{format_currency(float(cliente.saldo))}`\n"
        f"Saldo nuevo: `{format_currency(saldo_nuevo)}`\n"
        f"-----------------------\n"
        f"Confirmar el registro?"
    )
    await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=_build_confirm_keyboard())
    return PRESTAMO_CONF

async def prestamo_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ejecuta el prestamo via API."""
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_no":
        context.user_data.clear()
        await query.edit_message_text("Operacion cancelada.")
        return ConversationHandler.END

    cliente = context.user_data['cliente']
    monto = context.user_data['monto']
    descripcion = context.user_data.get('descripcion', '')

    await query.edit_message_text("Registrando prestamo...")

    try:
        result = await _call_api("POST", "/api/movimientos", {
            "cliente_id": str(cliente.id),
            "tipo": "prestamo",
            "monto": monto,
            "descripcion": descripcion or "Prestamo registrado por Telegram"
        })
        data = result.get("data", result)
        resumen = db.get_resumen_cliente(str(cliente.id))
        saldo_nuevo = resumen.get("saldo", float(cliente.saldo) + monto)

        comprobante = (
            f"PRESTAMO REGISTRADO EXITOSAMENTE\n"
            f"-----------------------\n"
            f"Recibo #: `{data.get('id', '-')[:8]}...`\n"
            f"Cliente: {cliente.nombre}\n"
            f"Monto: `{format_currency(monto)}`\n"
            f"Descripcion: {descripcion or '-'}\n"
            f"-----------------------\n"
            f"Saldo anterior: `{format_currency(float(cliente.saldo))}`\n"
            f"Saldo actual: `{format_currency(saldo_nuevo)}`\n"
            f"-----------------------\n"
            f"{datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            f"-----------------------\n"
            f"/start - Menu principal"
        )
        await query.edit_message_text(comprobante, parse_mode="Markdown")
    except ValueError as e:
        await query.edit_message_text(f"Error al registrar prestamo:\n{str(e)}", parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error registrando prestamo: {e}", exc_info=True)
        await query.edit_message_text("Error inesperado al registrar el prestamo.")

    context.user_data.clear()
    return ConversationHandler.END

# ==================== FSM: GASTO ====================

CATEGORIAS_GASTO = ["Arriendo", "Servicios", "Insumos", "Transporte", "Alimentacion", "Mantenimiento", "Papeleria", "Otros"]

@role_required("super_admin", "admin")
async def gasto_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo de registro de gasto."""
    context.user_data.clear()
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"gasto_cat:{i}")] for i, cat in enumerate(CATEGORIAS_GASTO)]
    keyboard.append([InlineKeyboardButton("Cancelar", callback_data="cancel_op")])
    await update.message.reply_text(
        "Registro de Gasto - Paso 1/3\n\n"
        "Selecciona la categoria del gasto:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return GASTO_CATEGORIA

async def gasto_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback cuando el usuario selecciona una categoria."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "cancel_op":
        context.user_data.clear()
        await query.edit_message_text("Operacion cancelada.")
        return ConversationHandler.END

    idx = int(data.split(":")[1])
    categoria = CATEGORIAS_GASTO[idx]
    context.user_data['categoria'] = categoria
    await query.edit_message_text(
        f"Gasto - Paso 2/3\n\n"
        f"Categoria: {categoria}\n\n"
        f"Cual es el monto del gasto?",
        parse_mode="Markdown",
        reply_markup=_build_cancel_keyboard()
    )
    return GASTO_MONTO

async def gasto_monto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el monto del gasto."""
    text = update.message.text.strip()
    cancel_btn = _build_cancel_keyboard()
    try:
        monto = float(text.replace("$", "").replace(".", "").replace(",", ".").strip())
        if monto <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "Monto invalido. Ingresa un numero valido mayor a 0.\nEjemplo: 50000",
            parse_mode="Markdown",
            reply_markup=cancel_btn
        )
        return GASTO_MONTO

    context.user_data['monto'] = monto
    await update.message.reply_text(
        f"Gasto - Paso 3/3\n\n"
        f"Categoria: {context.user_data['categoria']}\n"
        f"Monto: `{format_currency(monto)}`\n\n"
        f"Descripcion del gasto:",
        parse_mode="Markdown",
        reply_markup=_build_cancel_keyboard()
    )
    return GASTO_DESC

async def gasto_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe la descripcion y muestra resumen del gasto."""
    desc = update.message.text.strip()
    context.user_data['descripcion'] = desc
    categoria = context.user_data['categoria']
    monto = context.user_data['monto']

    texto = (
        f"Resumen del Gasto\n"
        f"-----------------------\n"
        f"Categoria: {categoria}\n"
        f"Monto: `{format_currency(monto)}`\n"
        f"Descripcion: {desc}\n"
        f"-----------------------\n"
        f"Confirmar el registro?"
    )
    await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=_build_confirm_keyboard())
    return GASTO_CONF

async def gasto_confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ejecuta el registro del gasto usando DatabaseManager."""
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_no":
        context.user_data.clear()
        await query.edit_message_text("Operacion cancelada.")
        return ConversationHandler.END

    categoria = context.user_data['categoria']
    monto = context.user_data['monto']
    descripcion = context.user_data.get('descripcion', '')

    await query.edit_message_text("Registrando gasto...")

    try:
        gasto = db.registrar_gasto(categoria=categoria, monto=monto, descripcion=descripcion)
        comprobante = (
            f"GASTO REGISTRADO EXITOSAMENTE\n"
            f"-----------------------\n"
            f"Categoria: {categoria}\n"
            f"Monto: `{format_currency(monto)}`\n"
            f"Descripcion: {descripcion or '-'}\n"
            f"-----------------------\n"
            f"{datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
            f"-----------------------\n"
            f"/start - Menu principal"
        )
        await query.edit_message_text(comprobante, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error registrando gasto: {e}", exc_info=True)
        await query.edit_message_text("Error inesperado al registrar el gasto.")

    context.user_data.clear()
    return ConversationHandler.END


# ==================== COMANDOS DE ADMINISTRACION DE USUARIOS ====================

@role_required("super_admin")
async def usuarios_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra la lista de usuarios registrados en el bot."""
    try:
        users = telegram_user_repo.get_all()
        if not users:
            await update.message.reply_text(
                "📋 *Usuarios*\n\nNo hay usuarios registrados.",
                parse_mode="Markdown",
                reply_markup=MAIN_KEYBOARD,
            )
            return

        lineas = ["📋 *Usuarios del Bot:*\n"]
        for u in users:
            activo = "🟢" if u["activo"] else "🔴"
            lineas.append(
                f"{activo} `{u['telegram_id']}` — **{u['nombre']}** — `{u['rol']}`"
            )
        lineas.append(f"\nTotal: {len(users)} usuarios")
        await update.message.reply_text(
            "\n".join(lineas),
            parse_mode="Markdown",
            reply_markup=MAIN_KEYBOARD,
        )
    except Exception as e:
        logger.error(f"Error en /usuarios: {e}", exc_info=True)
        await update.message.reply_text("❌ Error al listar usuarios.", reply_markup=MAIN_KEYBOARD)


@role_required("super_admin")
async def adduser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Agrega un nuevo usuario al bot.
    Uso: /adduser <telegram_id> <nombre> [rol]
    Roles: super_admin, admin, operador (default: operador)
    """
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "❌ *Uso:* `/adduser <telegram_id> <nombre> [rol]`\n\n"
            "Roles disponibles: `super_admin`, `admin`, `operador`\n"
            "Ejemplo: `/adduser 123456789 Juan Perez admin`",
            parse_mode="Markdown",
        )
        return

    try:
        telegram_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ El `telegram_id` debe ser un número entero.\n"
            "Ejemplo: `/adduser 123456789 Juan Perez`",
            parse_mode="Markdown",
        )
        return

    nombre = args[1]
    rol = args[2].lower() if len(args) >= 3 else "operador"

    if rol not in ("super_admin", "admin", "operador"):
        await update.message.reply_text(
            f"❌ Rol inválido: `{rol}`.\n"
            "Roles válidos: `super_admin`, `admin`, `operador`",
            parse_mode="Markdown",
        )
        return

    existing = telegram_user_repo.get_by_telegram_id(telegram_id)
    if existing:
        await update.message.reply_text(
            f"⚠️ El usuario `{telegram_id}` ya existe como **{existing['rol']}**.\n"
            "Usa `/permisos` para cambiar su rol.",
            parse_mode="Markdown",
        )
        return

    telegram_user_repo.create(TelegramUserCreate(
        telegram_id=telegram_id,
        nombre=nombre,
        rol=rol,
        activo=True,
    ))
    await update.message.reply_text(
        f"✅ *Usuario creado exitosamente:*\n"
        f"ID: `{telegram_id}`\n"
        f"Nombre: **{nombre}**\n"
        f"Rol: `{rol}`",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )


@role_required("super_admin")
async def deluser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Elimina o desactiva un usuario del bot.
    Uso: /deluser <telegram_id>
    """
    if not context.args:
        await update.message.reply_text(
            "❌ *Uso:* `/deluser <telegram_id>`\n"
            "Ejemplo: `/deluser 123456789`",
            parse_mode="Markdown",
        )
        return

    try:
        telegram_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ El `telegram_id` debe ser un número entero.",
            parse_mode="Markdown",
        )
        return

    if telegram_id == update.effective_user.id:
        await update.message.reply_text(
            "❌ No puedes eliminarte a ti mismo.",
            parse_mode="Markdown",
        )
        return

    existing = telegram_user_repo.get_by_telegram_id(telegram_id)
    if not existing:
        await update.message.reply_text(
            f"❌ El usuario `{telegram_id}` no existe.",
            parse_mode="Markdown",
        )
        return

    telegram_user_repo.delete(telegram_id)
    await update.message.reply_text(
        f"✅ Usuario `{telegram_id}` (**{existing['nombre']}**) eliminado.",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )


@role_required("super_admin")
async def permisos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra o cambia el rol de un usuario.
    Uso: /permisos [telegram_id] [nuevo_rol]
    Si no se pasa telegram_id, muestra los permisos del usuario actual.

    Roles: super_admin, admin, operador
    """
    args = context.args

    # Sin argumentos: muestra los roles disponibles
    if not args:
        texto = (
            "🔐 *Sistema de Permisos*\n\n"
            "**Roles disponibles:**\n"
            "  👑 `super_admin` — Acceso completo\n"
            "  🛡️ `admin` — Gestión operativa\n"
            "  👤 `operador` — Consultas y registros básicos\n\n"
            "*Comandos:*\n"
            "  `/permisos <id> [rol]` — Ver o cambiar rol\n"
            "  `/usuarios` — Listar usuarios\n"
            "  `/adduser <id> <nombre> [rol]` — Agregar usuario\n"
            "  `/deluser <id>` — Eliminar usuario"
        )
        await update.message.reply_text(texto, parse_mode="Markdown")
        return

    try:
        telegram_id = int(args[0])
    except ValueError:
        await update.message.reply_text(
            "❌ El `telegram_id` debe ser un número entero.",
            parse_mode="Markdown",
        )
        return

    user_data = telegram_user_repo.get_by_telegram_id(telegram_id)

    # Solo un argumento (telegram_id): mostrar el usuario
    if len(args) == 1:
        if not user_data:
            await update.message.reply_text(
                f"❌ El usuario `{telegram_id}` no está registrado.",
                parse_mode="Markdown",
            )
            return
        activo = "🟢 Activo" if user_data["activo"] else "🔴 Inactivo"
        await update.message.reply_text(
            f"👤 *Usuario:* **{user_data['nombre']}**\n"
            f"ID: `{user_data['telegram_id']}`\n"
            f"Rol: `{user_data['rol']}`\n"
            f"Estado: {activo}\n"
            f"Registro: {user_data['fecha_registro']}",
            parse_mode="Markdown",
        )
        return

    # Dos argumentos: cambiar rol
    nuevo_rol = args[1].lower()
    if nuevo_rol not in ("super_admin", "admin", "operador"):
        await update.message.reply_text(
            f"❌ Rol inválido: `{nuevo_rol}`.\n"
            "Roles válidos: `super_admin`, `admin`, `operador`",
            parse_mode="Markdown",
        )
        return

    if not user_data:
        await update.message.reply_text(
            f"❌ El usuario `{telegram_id}` no está registrado.\n"
            "Usa `/adduser` para crearlo primero.",
            parse_mode="Markdown",
        )
        return

    telegram_user_repo.update_rol(telegram_id, nuevo_rol)
    await update.message.reply_text(
        f"✅ Rol actualizado para `{telegram_id}` (**{user_data['nombre']}**):\n"
        f"`{user_data['rol']}` → `{nuevo_rol}`",
        parse_mode="Markdown",
        reply_markup=MAIN_KEYBOARD,
    )


# ==================== PUNTO DE ENTRADA PRINCIPAL ====================

def _ensure_super_admin():
    """Registra al TELEGRAM_ADMIN_ID como super_admin si no existe en BD."""
    try:
        existing = telegram_user_repo.get_by_telegram_id(TELEGRAM_ADMIN_ID)
        if not existing:
            telegram_user_repo.create(TelegramUserCreate(
                telegram_id=TELEGRAM_ADMIN_ID,
                nombre="Super Admin",
                rol="super_admin",
                activo=True,
            ))
            logger.info(f"Super admin registrado automáticamente con ID: {TELEGRAM_ADMIN_ID}")
        elif existing["rol"] != "super_admin":
            telegram_user_repo.update_rol(TELEGRAM_ADMIN_ID, "super_admin")
            logger.info(f"Usuario {TELEGRAM_ADMIN_ID} actualizado a super_admin")
    except Exception as e:
        logger.error(f"Error registrando super admin: {e}", exc_info=True)


def _registrar_handlers(application):
    """Registra todos los handlers en la aplicación. No modificar: lógica del bot."""
    cancel_handler = CommandHandler("cancelar", cancelar_operation)
    cancel_callback_handler = CallbackQueryHandler(cancelar_operation_callback, pattern="^cancel_op$")
    cancel_fallbacks = [cancel_handler, cancel_callback_handler]

    abono_conv = ConversationHandler(
        entry_points=[
            CommandHandler("abono", abono_entry),
            MessageHandler(filters.Regex("^📥 Abono$"), abono_entry)
        ],
        states={
            ABONO_BUSCAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, abono_buscar)],
            ABONO_SEL: [CallbackQueryHandler(abono_seleccionar, pattern="^abono_")],
            ABONO_MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, abono_monto)],
            ABONO_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, abono_desc)],
            ABONO_CONF: [CallbackQueryHandler(abono_confirmar, pattern="^(confirm_yes|confirm_no)$")],
        },
        fallbacks=cancel_fallbacks,
        conversation_timeout=CONV_TIMEOUT,
        name="abono_conversation",
    )

    prestamo_conv = ConversationHandler(
        entry_points=[
            CommandHandler("prestamo", prestamo_entry),
            MessageHandler(filters.Regex("^📤 Préstamo$"), prestamo_entry)
        ],
        states={
            PRESTAMO_BUSCAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, prestamo_buscar)],
            PRESTAMO_SEL: [CallbackQueryHandler(prestamo_seleccionar, pattern="^prestamo_")],
            PRESTAMO_MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, prestamo_monto)],
            PRESTAMO_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, prestamo_desc)],
            PRESTAMO_CONF: [CallbackQueryHandler(prestamo_confirmar, pattern="^(confirm_yes|confirm_no)$")],
        },
        fallbacks=cancel_fallbacks,
        conversation_timeout=CONV_TIMEOUT,
        name="prestamo_conversation",
    )

    gasto_conv = ConversationHandler(
        entry_points=[
            CommandHandler("gasto", gasto_entry),
            MessageHandler(filters.Regex("^🧾 Gasto$"), gasto_entry)
        ],
        states={
            GASTO_CATEGORIA: [CallbackQueryHandler(gasto_categoria, pattern="^gasto_cat:|^cancel_op$")],
            GASTO_MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, gasto_monto)],
            GASTO_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, gasto_desc)],
            GASTO_CONF: [CallbackQueryHandler(gasto_confirmar, pattern="^(confirm_yes|confirm_no)$")],
        },
        fallbacks=cancel_fallbacks,
        conversation_timeout=CONV_TIMEOUT,
        name="gasto_conversation",
    )

    application.add_handler(abono_conv)
    application.add_handler(prestamo_conv)
    application.add_handler(gasto_conv)
    application.add_handler(cancel_handler)
    application.add_handler(CommandHandler("cliente", cliente_command))
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("saldo_cliente", saldo_cliente_command))
    application.add_handler(CommandHandler("saldo_proveedor", saldo_proveedor_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, keyboard_button_handler))
    application.add_handler(CommandHandler("usuarios", usuarios_command))
    application.add_handler(CommandHandler("adduser", adduser_command))
    application.add_handler(CommandHandler("deluser", deluser_command))
    application.add_handler(CommandHandler("permisos", permisos_command))


def iniciar_bot() -> dict:
    """Inicializa y ejecuta el bot en modo Long Polling (bloqueante).
    Retorna {'ok': bool, 'mensaje': str}.
    """
    global _application, _bot_running
    logger.info("Iniciando EnOrden Telegram Bot...")

    _ensure_super_admin()

    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        _registrar_handlers(application)
        _application = application
        _bot_running = True

        logger.info(f"Bot en línea listo para recibir mensajes. Administrador ID: {TELEGRAM_ADMIN_ID}")
        print("\n" + "="*50)
        print("   ENORDEN - BOT DE TELEGRAM")
        print("   Sistema iniciado y escuchando consultas...")
        print(f"   Administrador ID: {TELEGRAM_ADMIN_ID}")
        print("="*50 + "\n")

        application.run_polling()
        _bot_running = False
        return {"ok": True, "mensaje": "Bot finalizado normalmente"}
    except Exception as e:
        _bot_running = False
        logger.error(f"Error ejecutando el bot: {e}", exc_info=True)
        return {"ok": False, "mensaje": str(e)}


def detener_bot():
    """Detiene el bot si está en ejecución."""
    global _application, _bot_running
    if _application:
        try:
            _application.stop()
        except Exception:
            pass
        _application = None
    _bot_running = False


def main():
    """Punto de entrada legacy para ejecución manual: python telegram_bot.py"""
    config = validar_configuracion()
    if not config["ok"]:
        logger.critical(f"Error de configuración: {config['mensaje']}")
        return
    result = iniciar_bot()
    if not result["ok"]:
        return


if __name__ == "__main__":
    main()
