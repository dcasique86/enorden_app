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
from typing import Any

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
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes
except ImportError:
    logger.critical(
        "Error: La librería 'python-telegram-bot' no está instalada.\n"
        "Por favor ejecuta: pip install python-telegram-bot"
    )
    sys.exit(1)

# Importar repositorios de EnOrden
try:
    from repository import cliente_repo, proveedor_repo
except ImportError:
    # Agregar el directorio actual al path en caso de ejecutarse desde fuera de su carpeta
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from repository import cliente_repo, proveedor_repo

# Leer y validar credenciales de variables de entorno
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ADMIN_ID_RAW = os.getenv("TELEGRAM_ADMIN_ID")

if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here" or TELEGRAM_BOT_TOKEN == "TU_TELEGRAM_BOT_TOKEN_AQUI":
    logger.critical("Error: TELEGRAM_BOT_TOKEN no configurado en el archivo .env")
    print("\n[ERROR] Por favor configura el TOKEN del bot en tu archivo .env antes de iniciar.")
    sys.exit(1)

if not TELEGRAM_ADMIN_ID_RAW or TELEGRAM_ADMIN_ID_RAW == "your_telegram_admin_id_here" or TELEGRAM_ADMIN_ID_RAW == "TU_TELEGRAM_ID_AQUI":
    logger.critical("Error: TELEGRAM_ADMIN_ID no configurado en el archivo .env")
    print("\n[ERROR] Por favor configura el ID de Administrador (TELEGRAM_ADMIN_ID) en tu archivo .env.")
    sys.exit(1)

try:
    TELEGRAM_ADMIN_ID = int(TELEGRAM_ADMIN_ID_RAW)
except ValueError:
    logger.critical(f"Error: TELEGRAM_ADMIN_ID '{TELEGRAM_ADMIN_ID_RAW}' no es un número de ID válido.")
    sys.exit(1)

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

# ==================== SEGURIDAD ====================

def admin_only(func):
    """Decorador de seguridad para restringir el acceso exclusivamente al ID administrador configurado."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            logger.warning("Intento de comando recibido sin datos de usuario.")
            return

        if user.id != TELEGRAM_ADMIN_ID:
            logger.warning(f"Acceso denegado para el usuario ID: {user.id} (@{user.username or 'S/N'})")
            # Responder con mensaje de acceso denegado estático sin revelar datos
            if update.message:
                await update.message.reply_text(
                    "❌ *Acceso denegado.*\n"
                    "Este bot es de uso administrativo privado y exclusivo para el propietario del sistema.",
                    parse_mode="Markdown"
                )
            return

        return await func(update, context, *args, **kwargs)
    return wrapper

# ==================== HANDLERS DE COMANDOS ====================

@admin_only
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start: Mensaje de bienvenida y ayuda de comandos."""
    help_text = (
        "🤖 *EnOrden - Bot de Consulta Administrativa*\n\n"
        "¡Conexión establecida con la base de datos SQLite! 🟢\n"
        "Este bot está listo para consultas de saldos internos.\n\n"
        "📋 *Comandos disponibles:*\n"
        "👤 `/saldo_cliente <nombre>` - Buscar cliente y ver saldo\n"
        "🏭 `/saldo_proveedor <nombre>` - Buscar proveedor y ver deuda\n"
        "❓ `/help` - Ver esta ayuda"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

@admin_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help: Ayuda de comandos."""
    await start_command(update, context)

@admin_only
async def saldo_cliente_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /saldo_cliente <nombre o apellido>: Busca clientes y muestra su saldo."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ *Uso incorrecto:*\n"
            "Usa `/saldo_cliente <Nombre o Apellido>` para realizar la búsqueda.\n"
            "Ejemplo: `/saldo_cliente denis`",
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
            # Un solo resultado encontrado: Mostrar reporte detallado
            c = clientes[0]
            
            estado = "🟢 Activo" if c.activo else "🔴 Inactivo"
            dias_sin_abono = f"{c.dias_sin_abonar} días" if c.dias_sin_abonar is not None else "Sin abonos registrados"
            ultimo_abono_fmt = "Ninguno"
            
            if c.ultimo_abono:
                ultimo_abono_fmt = f"{format_currency(c.ultimo_abono.monto)} ({c.ultimo_abono.fecha})"

            mensaje = (
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
                f"💰 *Último Abono:* {ultimo_abono_fmt}\n"
                f"==========================="
            )
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

@admin_only
async def saldo_proveedor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /saldo_proveedor <nombre o apellido>: Busca proveedores y muestra la deuda."""
    if not context.args:
        await update.message.reply_text(
            "⚠️ *Uso incorrecto:*\n"
            "Usa `/saldo_proveedor <Nombre o Apellido>` para realizar la búsqueda.\n"
            "Ejemplo: `/saldo_proveedor distribuidora`",
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
            # Un solo resultado encontrado: Mostrar reporte detallado
            p = proveedores[0]
            
            estado = "🟢 Activo" if p.activo else "🔴 Inactivo"

            mensaje = (
                f"🏭 *Detalle del Proveedor*\n"
                f"===========================\n"
                f"📛 *Nombre:* {p.nombre}\n"
                f"📞 *Teléfono:* {p.telefono or 'No registrado'}\n"
                f"📌 *Estado:* {estado}\n"
                f"---------------------------\n"
                f"🧡 *Deuda Actual:* `{format_currency(p.saldo)}`\n"
                f"📄 *Total Facturas:* {format_currency(p.total_facturas)}\n"
                f"💸 *Total Pagado:* {format_currency(p.total_pagado)}\n"
                f"==========================="
            )
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

# ==================== PUNTO DE ENTRADA PRINCIPAL ====================

def main():
    """Inicializa y ejecuta el bot en modo Long Polling."""
    logger.info("Iniciando EnOrden Telegram Bot...")
    
    try:
        # Construir la aplicación
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Registrar los handlers de comandos
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("saldo_cliente", saldo_cliente_command))
        application.add_handler(CommandHandler("saldo_proveedor", saldo_proveedor_command))

        logger.info(f"Bot en línea listo para recibir mensajes. Administrador autorizado ID: {TELEGRAM_ADMIN_ID}")
        print("\n" + "="*50)
        print("   ENORDEN - BOT DE TELEGRAM")
        print("   Sistema iniciado y escuchando consultas...")
        print(f"   Administrador ID: {TELEGRAM_ADMIN_ID}")
        print("   Presiona Ctrl+C para detener.")
        print("="*50 + "\n")

        # Ejecutar por Long Polling
        application.run_polling()
        
    except Exception as e:
        logger.critical(f"Error crítico ejecutando el bot: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
