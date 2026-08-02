from typing import Optional
from .conversation import ConversationManager, ConversationSession
from .intent_detector import detect_intent
from .handlers.cliente import (
    buscar_clientes,
    obtener_saldo,
    obtener_ficha,
    obtener_historial,
    obtener_ultimos_pagos,
    obtener_prestamos,
    obtener_resumen,
)


class AssistantEngine:
    def __init__(self):
        self.conversation = ConversationManager()

    def process_message(self, session_id: Optional[str], text: str) -> dict:
        session = self.conversation.get_or_create(session_id)

        intent = detect_intent(text)
        session.current_intent = intent

        if intent == "buscar_cliente":
            return self._handle_buscar_cliente(session, text)

        if session.selected_cliente_id is None:
            return {
                "type": "ask_cliente",
                "message": "Primero dime a qué cliente quieres consultar.",
                "session_id": session.session_id,
            }

        handlers = {
            "saldo": self._handle_saldo,
            "historial": self._handle_historial,
            "pagos": self._handle_pagos,
            "prestamos": self._handle_prestamos,
            "resumen": self._handle_resumen,
            "ficha": self._handle_ficha,
        }

        handler = handlers.get(intent)
        if handler:
            return handler(session)

        return self._handle_buscar_cliente(session, text)

    def _handle_buscar_cliente(self, session: ConversationSession, text: str) -> dict:
        results = buscar_clientes(text)
        session.search_results = results

        if not results:
            return {
                "type": "no_results",
                "message": f"No encontré ningún cliente que coincida con \"{text}\".",
                "session_id": session.session_id,
            }

        if len(results) == 1:
            c = results[0]
            session.select_cliente(c["id"], c["nombre"])
            return {
                "type": "cliente_unico",
                "cliente": c,
                "message": f"Cliente encontrado: **{c['nombre']}**",
                "session_id": session.session_id,
            }

        return {
            "type": "cliente_lista",
            "clientes": results,
            "message": f"Encontré {len(results)} clientes. Selecciona uno:",
            "session_id": session.session_id,
        }

    def select_cliente(self, session_id: str, cliente_id: str) -> dict:
        session = self.conversation.get_or_create(session_id)
        results = buscar_clientes("")
        match = next((c for c in results if c["id"] == cliente_id), None)

        if not match:
            c = obtener_ficha(cliente_id)
            if c:
                match = c

        if not match:
            return {
                "type": "error",
                "message": "Cliente no encontrado.",
                "session_id": session.session_id,
            }

        session.select_cliente(match["id"], match["nombre"])
        return {
            "type": "cliente_seleccionado",
            "cliente": match,
            "message": f"Cliente seleccionado: **{match['nombre']}**",
            "session_id": session.session_id,
        }

    def _handle_saldo(self, session: ConversationSession) -> dict:
        data = obtener_saldo(session.selected_cliente_id)
        if not data:
            return {"type": "error", "message": "No pude obtener el saldo.", "session_id": session.session_id}
        return {
            "type": "saldo",
            "data": data,
            "cliente_nombre": session.selected_cliente_nombre,
            "session_id": session.session_id,
        }

    def _handle_historial(self, session: ConversationSession) -> dict:
        data = obtener_historial(session.selected_cliente_id)
        return {
            "type": "historial",
            "data": data,
            "cliente_nombre": session.selected_cliente_nombre,
            "session_id": session.session_id,
        }

    def _handle_pagos(self, session: ConversationSession) -> dict:
        data = obtener_ultimos_pagos(session.selected_cliente_id)
        return {
            "type": "pagos",
            "data": data,
            "cliente_nombre": session.selected_cliente_nombre,
            "session_id": session.session_id,
        }

    def _handle_prestamos(self, session: ConversationSession) -> dict:
        data = obtener_prestamos(session.selected_cliente_id)
        return {
            "type": "prestamos",
            "data": data,
            "cliente_nombre": session.selected_cliente_nombre,
            "session_id": session.session_id,
        }

    def _handle_resumen(self, session: ConversationSession) -> dict:
        data = obtener_resumen(session.selected_cliente_id)
        if not data:
            return {"type": "error", "message": "No pude obtener el resumen.", "session_id": session.session_id}
        return {
            "type": "resumen",
            "data": data,
            "cliente_nombre": session.selected_cliente_nombre,
            "session_id": session.session_id,
        }

    def _handle_ficha(self, session: ConversationSession) -> dict:
        data = obtener_ficha(session.selected_cliente_id)
        if not data:
            return {"type": "error", "message": "No pude obtener la ficha.", "session_id": session.session_id}
        return {
            "type": "ficha",
            "data": data,
            "cliente_nombre": session.selected_cliente_nombre,
            "session_id": session.session_id,
        }

    def clear_session(self, session_id: str):
        session = self.conversation.get(session_id)
        if session:
            session.reset()