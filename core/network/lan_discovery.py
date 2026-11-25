"""Stdlib UDP broadcast LAN auto-discovery for Librarian Management."""

import json
import socket
import threading
import time
from typing import Any, Dict, Optional

from core.network.booth_config import DEFAULT_DISCOVERY_PORT
from core.shared.version import APP_VERSION

DISCOVERY_MAGIC = b"SMTE_DISCOVER_LIBRARIAN"
_SERVICE_NAME = "smte-librarian"


def _parse_reply(raw: bytes, sender_ip: str) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("service") != _SERVICE_NAME:
        return None
    port = data.get("port")
    if not isinstance(port, int) or isinstance(port, bool) or not (1 <= port <= 65535):
        return None
    return {
        "host": sender_ip,
        "port": port,
        "version": str(data.get("version", "")),
    }


class LanDiscoveryResponder:
    """Background UDP listener replying to Booth discovery broadcasts."""

    def __init__(
        self,
        http_port: int,
        discovery_port: int = DEFAULT_DISCOVERY_PORT,
        bind_host: str = "",
    ) -> None:
        self.http_port = int(http_port)
        self._requested_port = int(discovery_port)
        self.bind_host = bind_host
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    @property
    def discovery_port(self) -> int:
        if self._sock is not None:
            return int(self._sock.getsockname()[1])
        return self._requested_port

    def start(self) -> None:
        if self._sock is not None:
            return
        self._stop_event.clear()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(0.2)
        sock.bind((self.bind_host, self._requested_port))
        self._sock = sock
        self._thread = threading.Thread(target=self._serve_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def _serve_loop(self) -> None:
        payload = json.dumps(
            {"service": _SERVICE_NAME, "port": self.http_port, "version": APP_VERSION}
        ).encode("utf-8")
        while not self._stop_event.is_set() and self._sock is not None:
            try:
                data, addr = self._sock.recvfrom(1024)
            except socket.timeout:
                continue
            except OSError:
                break
            if data.strip() == DISCOVERY_MAGIC:
                try:
                    self._sock.sendto(payload, addr)
                except OSError:
                    pass


def _recv_until_match(sock: socket.socket, timeout: float) -> Optional[Dict[str, Any]]:
    deadline = time.monotonic() + float(timeout)
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        sock.settimeout(remaining)
        raw, addr = sock.recvfrom(1024)
        parsed = _parse_reply(raw, addr[0])
        if parsed is not None:
            return parsed


def discover_librarian(
    discovery_port: int = DEFAULT_DISCOVERY_PORT,
    timeout: float = 1.5,
    broadcast_addr: str = "<broadcast>",
) -> Optional[Dict[str, Any]]:
    """Broadcast a discovery packet and return the first valid server reply or None."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(DISCOVERY_MAGIC, (broadcast_addr, int(discovery_port)))
        return _recv_until_match(sock, timeout)
    except (socket.timeout, OSError):
        return None
    finally:
        sock.close()
