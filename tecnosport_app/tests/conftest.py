import os
import sys
import tempfile
import shutil

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import DatabaseManager
from repository import ExcelClienteRepository, ExcelProveedorRepository


@pytest.fixture(autouse=True)
def httpx_compat(monkeypatch):
    """Compatibilidad del httpx instalado (no acepta `app=` en Client).

    Starlette 0.35 pasa `app=` a httpx.Client al construir TestClient; el
    httpx local lo rechaza. El transporte ASGI ya liga la app internamente,
    así que descartar el kwarg es seguro.
    """
    import httpx

    original_init = httpx.Client.__init__

    def _init(self, *args, **kwargs):
        kwargs.pop("app", None)
        return original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "__init__", _init)


def _crear_excel_template(excel_path):
    """Crea el archivo Excel con las hojas esperadas por DatabaseManager."""
    from openpyxl import Workbook
    wb = Workbook()
    for nombre in ("clientes", "movimientos", "proveedores", "movimientos_proveedores",
                   "productos", "ventas", "config", "gastos"):
        if nombre == "clientes":
            ws = wb.active
            ws.title = nombre
        else:
            wb.create_sheet(nombre)
    wb.save(excel_path)
    wb.close()


@pytest.fixture
def data_dir():
    path = tempfile.mkdtemp(prefix="enorden_test_")
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def db(data_dir):
    _crear_excel_template(os.path.join(data_dir, "datos_tecnosport.xlsx"))
    manager = DatabaseManager(data_dir)
    from services.migraciones import ejecutar_migraciones
    ejecutar_migraciones(manager)
    yield manager
    try:
        manager.get_connection().close()
    except Exception:
        pass


@pytest.fixture
def proveedor_repo(db):
    return ExcelProveedorRepository(db)


@pytest.fixture
def client(data_dir, monkeypatch):
    """TestClient de la API FastAPI con base de datos temporal aislada.

    Reemplaza el `db` global de main por una instancia con datos en un
    directorio temporal y neutraliza el arranque de servicios externos
    (Telegram, scheduler) del lifespan.
    """
    import main
    from fastapi.testclient import TestClient

    _crear_excel_template(os.path.join(data_dir, "datos_tecnosport.xlsx"))
    main_db = DatabaseManager(data_dir)
    from services.migraciones import ejecutar_migraciones
    ejecutar_migraciones(main_db)

    monkeypatch.setattr(main, "db", main_db)
    monkeypatch.setattr(main.prestamo_service, "verificar_vencimientos", lambda: 0)
    monkeypatch.setattr(main.startup_manager, "iniciar_todo", lambda: None)
    monkeypatch.setattr(main.startup_manager, "detener_todo", lambda: None)
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def cliente_repo(db):
    return ExcelClienteRepository(db)
