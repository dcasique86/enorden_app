"""
EnOrden - Sistema de Backup Automático
Ejecuta backups automáticos con programación configurable:
- Activar/desactivar (config: backup_activo)
- Frecuencia diaria a una hora (config: backup_hora "HH:MM") o cada N horas
- Retención de copias (config: backup_mantener)
"""

import os
import sys
import time
import threading
from datetime import datetime, timedelta
from database import db


class BackupScheduler:
    """Programador de backups automáticos"""

    def __init__(self):
        self.running = False
        self.thread = None
        self.last_backup = None
        self.next_backup = None

    def start(self):
        """Inicia el programador de backups"""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        print("[OK] Programador de backups iniciado")

    def stop(self):
        """Detiene el programador"""
        self.running = False

    def reconfigurar(self):
        """Fuerza el recálculo de la próxima copia (tras guardar configuración)."""
        self.next_backup = None

    def _leer_config(self):
        """Lee la programación desde la tabla config con valores por defecto."""
        activo = (db.get_config("backup_activo", "true") or "true").strip().lower() == "true"
        hora = (db.get_config("backup_hora", "23:00") or "23:00").strip() or "23:00"
        frecuencia = (db.get_config("backup_frecuencia", "diario") or "diario").strip() or "diario"
        try:
            mantener = int(db.get_config("backup_mantener", "30") or "30")
        except (TypeError, ValueError):
            mantener = 30
        return activo, hora, frecuencia, mantener

    def _calcular_siguiente(self, now):
        """Calcula cuándo debe ejecutarse la próxima copia según la programación."""
        activo, hora, frecuencia, _ = self._leer_config()
        if not activo:
            return None

        if frecuencia in ("cada_6h", "cada_12h"):
            horas = 6 if frecuencia == "cada_6h" else 12
            if self.last_backup is None:
                return now + timedelta(hours=horas)
            return self.last_backup + timedelta(hours=horas)

        # Frecuencia diaria a la hora configurada
        try:
            hh, mm = (int(part) for part in hora.split(":"))
        except (ValueError, AttributeError):
            hh, mm = 23, 0
        objetivo = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if now >= objetivo:
            objetivo += timedelta(days=1)
        return objetivo

    def _run_scheduler(self):
        """Ejecuta el programador en segundo plano"""
        while self.running:
            now = datetime.now()
            try:
                self.next_backup = self._calcular_siguiente(now)

                if self.next_backup and now >= self.next_backup:
                    if self.last_backup is None or (now - self.last_backup).total_seconds() >= 55:
                        _, _, _, mantener = self._leer_config()
                        backup_path = db.crear_backup(mantener=mantener)
                        self.last_backup = now
                        self.next_backup = self._calcular_siguiente(now)
                        print(f"[Backup] Backup automatico creado: {backup_path}")
            except Exception as e:
                print(f"[Error] Error en backup automatico: {e}")

            # Verificar cada 30 segundos
            time.sleep(30)

    def estado(self) -> dict:
        """Devuelve el estado actual del programador para la UI."""
        activo, hora, frecuencia, mantener = self._leer_config()
        return {
            "activo": activo,
            "hora": hora,
            "frecuencia": frecuencia,
            "mantener": mantener,
            "ultimo_backup": self.last_backup.strftime("%Y-%m-%d %H:%M:%S") if self.last_backup else None,
            "proximo_backup": self.next_backup.strftime("%Y-%m-%d %H:%M:%S") if self.next_backup else None,
        }


# Instancia global
backup_scheduler = BackupScheduler()


def start_backup_scheduler():
    """Inicia el programador de backups"""
    backup_scheduler.start()


if __name__ == "__main__":
    # Crear backup manual
    print("Creando backup manual...")
    try:
        backup_path = db.crear_backup()
        print(f"[OK] Backup creado: {backup_path}")
    except Exception as e:
        print(f"[Error]: {e}")
