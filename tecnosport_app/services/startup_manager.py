"""
Startup Manager de EnOrden.

Orquesta el inicio de todos los componentes del sistema:
1. Servidor FastAPI
2. Bot de Telegram (con validación previa)
3. Scheduler de backups
4. Servicios internos (migraciones, verificación de vencimientos)

Proporciona auto-recuperación para el bot de Telegram.
"""

import threading
import time
import logging
from typing import Optional

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("StartupManager")


class StartupManager:
    """Gestiona el ciclo de vida de todos los servicios de EnOrden."""

    def __init__(self, db_instance):
        self._db = db_instance
        self._bot_thread: Optional[threading.Thread] = None
        self._bot_monitor_thread: Optional[threading.Thread] = None
        self._running = False
        self._bot_module = None

    # ── Telegram Bot ──────────────────────────────────────────────

    def _cargar_modulo_bot(self):
        """Importa telegram_bot de forma segura. Retorna el módulo o None."""
        try:
            import telegram_bot as bot
            return bot
        except Exception as e:
            logger.warning(f"No se pudo cargar el módulo del bot de Telegram: {e}")
            return None

    def _ejecutar_bot(self):
        """Ejecuta el bot (corre en un hilo separado)."""
        if not self._bot_module:
            logger.error("Módulo del bot no disponible, no se puede iniciar")
            return

        result = self._bot_module.iniciar_bot()
        if not result.get("ok"):
            logger.warning(f"Bot de Telegram terminó con error: {result.get('mensaje')}")

    def _monitorear_bot(self):
        """Monitorea el hilo del bot y lo reinicia si falla inesperadamente."""
        while self._running:
            if self._bot_thread and not self._bot_thread.is_alive():
                if self._running:
                    logger.warning("Bot de Telegram se detuvo inesperadamente. Reintentando en 10 segundos...")
                    time.sleep(10)
                    self._iniciar_bot_interno()

            if self._bot_module and hasattr(self._bot_module, '_bot_running'):
                pass

            time.sleep(5)

    def _iniciar_bot_interno(self):
        """Crea y arranca el hilo del bot."""
        if self._bot_thread and self._bot_thread.is_alive():
            logger.info("Bot de Telegram ya está en ejecución, no se inicia otro")
            return

        if not self._bot_module:
            self._bot_module = self._cargar_modulo_bot()
            if not self._bot_module:
                return

        config = self._bot_module.validar_configuracion()
        if not config.get("ok"):
            logger.warning(f"⚠ Telegram deshabilitado — {config.get('mensaje', 'configuración inválida')}")
            return

        self._bot_thread = threading.Thread(target=self._ejecutar_bot, daemon=True)
        self._bot_thread.start()
        logger.info(f"✓ Telegram iniciado (Admin ID: {config.get('admin_id', 'desconocido')})")

    def iniciar_telegram_bot(self):
        """Valida configuración e inicia el bot de Telegram en un hilo."""
        self._bot_module = self._cargar_modulo_bot()
        if not self._bot_module:
            return

        config = self._bot_module.validar_configuracion()
        if not config.get("ok"):
            logger.warning(f"⚠ Telegram deshabilitado — {config.get('mensaje', 'configuración inválida')}")
            return

        self._iniciar_bot_interno()

        self._bot_monitor_thread = threading.Thread(target=self._monitorear_bot, daemon=True)
        self._bot_monitor_thread.start()

    def detener_telegram_bot(self):
        """Detiene el bot de Telegram."""
        if self._bot_module and hasattr(self._bot_module, 'detener_bot'):
            try:
                self._bot_module.detener_bot()
                logger.info("Bot de Telegram detenido")
            except Exception as e:
                logger.warning(f"Error al detener el bot: {e}")

    # ── Scheduler ─────────────────────────────────────────────────

    def iniciar_scheduler(self):
        """Inicia el scheduler de backups si está disponible."""
        try:
            from scheduler import start_backup_scheduler
            start_backup_scheduler()
            logger.info("✓ Scheduler de backups iniciado")
        except ImportError:
            logger.info("Scheduler no disponible — backups automáticos desactivados")
        except Exception as e:
            logger.warning(f"No se pudo iniciar el scheduler: {e}")

    # ── Ciclo de vida completo ─────────────────────────────────────

    def iniciar_todo(self):
        """Inicia todos los servicios de EnOrden."""
        self._running = True
        logger.info("=" * 50)
        logger.info("  ENORDEN - INICIANDO SISTEMA")
        logger.info("=" * 50)

        self.iniciar_scheduler()
        self.iniciar_telegram_bot()

        logger.info("✓ Sistema listo")
        logger.info("=" * 50)

    def detener_todo(self):
        """Detiene todos los servicios."""
        self._running = False
        self.detener_telegram_bot()
        logger.info("Servicios detenidos")
