import os
import sys
import tempfile
import shutil

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import DatabaseManager
from repository import ExcelClienteRepository, ExcelProveedorRepository


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
    yield manager
    try:
        manager.get_connection().close()
    except Exception:
        pass


@pytest.fixture
def cliente_repo(db):
    return ExcelClienteRepository(db)


@pytest.fixture
def proveedor_repo(db):
    return ExcelProveedorRepository(db)
