import os
import time
from datetime import datetime, timedelta


class TestBackups:

    def test_crear_backup_crea_archivo(self, db):
        backup_path = db.crear_backup()
        assert os.path.exists(backup_path)
        assert backup_path.endswith(".db")

    def test_crear_backup_en_directorio_correcto(self, db):
        backup_path = db.crear_backup()
        assert os.path.dirname(backup_path) == db.backup_dir

    def test_backup_tiene_fecha_en_nombre(self, db):
        backup_path = db.crear_backup()
        hoy = datetime.now().strftime("%Y-%m-%d")
        assert hoy in os.path.basename(backup_path)

    def test_get_backups_lista_vacia_al_inicio(self, db):
        backups = db.get_backups()
        assert backups == []

    def test_get_backups_despues_de_crear(self, db):
        db.crear_backup()
        backups = db.get_backups()
        assert len(backups) == 1
        assert backups[0]["nombre"].endswith(".db")
        assert backups[0]["tamano"] > 0

    def test_get_backups_varios(self, db):
        for _ in range(3):
            db.crear_backup()
            time.sleep(1)
        backups = db.get_backups()
        assert len(backups) == 3

    def test_backup_tiene_metadatos(self, db):
        db.crear_backup()
        backups = db.get_backups()
        b = backups[0]
        assert "nombre" in b
        assert "fecha" in b
        assert "tamano" in b
        assert b["tamano"] > 0

    def test_limpiar_backups_antiguos_mantiene_n(self, db):
        for _ in range(5):
            db.crear_backup()
            time.sleep(1)
        # Antes de limpiar hay 5
        assert len(db.get_backups()) == 5
        # Limpiar manteniendo 3
        db._limpiar_backups_antiguos(mantener=3)
        backups = db.get_backups()
        assert len(backups) == 3

    def test_crear_backup_no_afecta_db_original(self, db):
        # Crear un cliente
        db.crear_cliente(nombre="Test Backup", telefono="111")
        assert len(db.get_clientes()) == 1
        # Crear backup
        db.crear_backup()
        # El cliente sigue existiendo
        assert len(db.get_clientes()) == 1

    def test_backup_database_integridad(self, db):
        db.crear_cliente(nombre="Para Backup", telefono="222")
        db.crear_backup()
        # El backup_dir debe contener un archivo .db
        archivos = [f for f in os.listdir(db.backup_dir) if f.endswith(".db")]
        assert len(archivos) >= 1
