import time
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, Set, Callable
from audioburst.utils.helpers import generate_session_id
from audioburst.utils.logger import log


@dataclass
class SessionState:
    session_id: int
    total_packets: int=0
    received_packets: Set[int]=field(default_factory=set)
    packets: Dict[int, bytes]=field(default_factory=dict)
    start_time: float=0.0
    last_packet_time: float=0.0
    enc_type: int=0
    active: bool=True
    lock: threading.Lock=field(default_factory=threading.Lock)

    def add_packet(self, seq_id: int, payload: bytes) -> bool:
        with self.lock:
            if seq_id in self.received_packets:
                return False
            self.received_packets.add(seq_id)
            self.packets[seq_id]=payload
            self.last_packet_time=time.time()
            return True

    def is_complete(self) -> bool:
        with self.lock:
            return len(self.received_packets) >= self.total_packets

    def get_ordered_payloads(self) -> list:
        with self.lock:
            return [self.packets[i] for i in range(self.total_packets) if i in self.packets]

    def missing_packets(self) -> Set[int]:
        with self.lock:
            return set(range(self.total_packets)) - self.received_packets

    def progress(self) -> float:
        with self.lock:
            if self.total_packets == 0:
                return 0.0
            return len(self.received_packets) / self.total_packets


class SessionManager:
    def __init__(self, timeout: float=30.0):
        self._sessions: Dict[int, SessionState]={}
        self._timeout=timeout
        self._lock=threading.Lock()
        self._on_complete: Optional[Callable]=None

    def create_session(self, total_packets: int, enc_type: int=0) -> SessionState:
        sid=generate_session_id()
        session=SessionState(
            session_id=sid,
            total_packets=total_packets,
            start_time=time.time(),
            last_packet_time=time.time(),
            enc_type=enc_type
        )
        with self._lock:
            self._sessions[sid]=session
        log.info(f"Session {sid} created: {total_packets} packets expected")
        return session

    def get_session(self, session_id: int) -> Optional[SessionState]:
        with self._lock:
            return self._sessions.get(session_id)

    def add_packet(self, session_id: int, seq_id: int, total_packets: int,
                   enc_type: int, payload: bytes) -> Optional[SessionState]:
        with self._lock:
            session=self._sessions.get(session_id)
            if session is None:
                session=SessionState(
                    session_id=session_id,
                    total_packets=total_packets,
                    start_time=time.time(),
                    last_packet_time=time.time(),
                    enc_type=enc_type
                )
                self._sessions[session_id]=session
            session.total_packets=max(session.total_packets, total_packets)
            session.enc_type=enc_type
        session.add_packet(seq_id, payload)
        if session.is_complete() and self._on_complete:
            self._on_complete(session)
        return session

    def set_complete_callback(self, callback: Callable) -> None:
        self._on_complete=callback

    def cleanup_expired(self) -> None:
        now=time.time()
        with self._lock:
            expired=[
                sid for sid, s in self._sessions.items()
                if now - s.last_packet_time > self._timeout
            ]
            for sid in expired:
                del self._sessions[sid]
                log.debug(f"Session {sid} expired and removed")

    def active_sessions(self) -> int:
        with self._lock:
            return len(self._sessions)
