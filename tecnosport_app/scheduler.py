"""
EnOrden - Sistema de Backup Automático
Ejecuta backups diarios de forma automática
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
    
    def _run_scheduler(self):
        """Ejecuta el programador en segundo plano"""
        while self.running:
            now = datetime.now()
            
            # Ejecutar backup a las 23:00 (11 PM)
            if now.hour == 23 and now.minute == 0:
                if self.last_backup is None or (now - self.last_backup).days >= 1:
                    try:
                        backup_path = db.crear_backup()
                        print(f"[Backup] Backup automatico creado: {backup_path}")
                        self.last_backup = now
                    except Exception as e:
                        print(f"[Error] Error en backup automatico: {e}")
            
            # Verificar cada minuto
            time.sleep(60)


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
