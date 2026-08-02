import uuid
from datetime import datetime, timedelta
from typing import Optional


class ConversationSession:
    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.selected_cliente_id: Optional[str] = None
        self.selected_cliente_nombre: Optional[str] = None
        self.current_intent: Optional[str] = None
        self.search_results: list = []
        self.step: Optional[str] = None

    def touch(self):
        self.last_activity = datetime.now()

    def select_cliente(self, cliente_id: str, nombre: str):
        self.selected_cliente_id = cliente_id
        self.selected_cliente_nombre = nombre
        self.step = "cliente_seleccionado"

    def clear_selection(self):
        self.selected_cliente_id = None
        self.selected_cliente_nombre = None
        self.step = None
        self.current_intent = None

    def is_expired(self, timeout_minutes: int = 15) -> bool:
        return datetime.now() - self.last_activity > timedelta(minutes=timeout_minutes)

    def reset(self):
        self.selected_cliente_id = None
        self.selected_cliente_nombre = None
        self.current_intent = None
        self.search_results = []
        self.step = None


class ConversationManager:
    def __init__(self, timeout_minutes: int = 15):
        self._sessions: dict[str, ConversationSession] = {}
        self._timeout = timeout_minutes

    def get_or_create(self, session_id: str = None) -> ConversationSession:
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            if not session.is_expired(self._timeout):
                session.touch()
                return session
        session = ConversationSession(session_id)
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Optional[ConversationSession]:
        session = self._sessions.get(session_id)
        if session and not session.is_expired(self._timeout):
            session.touch()
            return session
        return None

    def cleanup_expired(self):
        expired = [
            sid for sid, s in self._sessions.items()
            if s.is_expired(self._timeout)
        ]
        for sid in expired:
            del self._sessions[sid]