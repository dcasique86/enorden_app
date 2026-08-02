import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from assistant.engine import AssistantEngine
from assistant.conversation import ConversationManager
from assistant.intent_detector import detect_intent
from assistant.ui import UIRenderer


def test_engine_creates_session():
    engine = AssistantEngine()
    result = engine.process_message(None, "Luis")
    assert result["session_id"] is not None
    assert result["type"] in ("cliente_unico", "cliente_lista", "no_results")


def test_conversation_timeout():
    mgr = ConversationManager(timeout_minutes=0)
    session = mgr.get_or_create("test")
    import time
    time.sleep(0.001)
    assert session.is_expired(0) is True


def test_intent_detection():
    assert detect_intent("saldo") == "saldo"
    assert detect_intent("historial") == "historial"
    assert detect_intent("pagos") == "pagos"
    assert detect_intent("prestamos") == "prestamos"
    assert detect_intent("resumen") == "resumen"
    assert detect_intent("ficha") == "ficha"
    assert detect_intent("cualquier otra cosa") == "buscar_cliente"


def test_conversation_clear():
    mgr = ConversationManager()
    session = mgr.get_or_create("test_clear")
    session.select_cliente("123", "Test")
    assert session.selected_cliente_id == "123"
    session.reset()
    assert session.selected_cliente_id is None


def test_ui_render_saldo():
    data = {"saldo": 150000, "total_prestado": 500000, "total_abonado": 350000, "dias_sin_abonar": 5, "ultimo_abono": None}
    result = UIRenderer.render_saldo(data, "Test")
    assert "Test" in result
    assert "150" in result or "150.000" in result


def test_ui_render_ficha():
    data = {"nombre": "Juan", "id": "abc123", "telefono": "555", "fecha_creacion": "2024-01-01", "activo": True}
    result = UIRenderer.render_ficha(data)
    assert "Juan" in result
    assert "abc123" in result
    assert "Activo" in result


def test_ui_render_historial_vacio():
    result = UIRenderer.render_historial([], "Test")
    assert "Sin movimientos" in result


def test_ui_render_lista():
    clientes = [
        {"id": "1", "nombre": "A", "saldo": 0, "telefono": "111"},
        {"id": "2", "nombre": "B", "saldo": 100, "telefono": "222"},
    ]
    result = UIRenderer.render_cliente_lista(clientes, "test")
    assert "2 clientes" in result
    assert "A" in result