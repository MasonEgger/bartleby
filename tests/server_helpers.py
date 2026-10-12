# ABOUTME: Shared helpers that run a DevServer on a worker thread for the server tests.
# Both the server tests and the smoke test start the real server the same way.

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bartleby.server import DevServer


def start_running_server(server: DevServer) -> tuple[threading.Thread, int]:
    """Start ``server.run`` on a daemon thread and block until it is listening.

    The ``ready`` callback fires once the socket is listening and the watcher
    is running, handing back the bound port.

    :param server: A configured, not-yet-running ``DevServer``.
    :returns: The worker thread and the bound ephemeral port.
    """
    bound: list[int] = []
    listening = threading.Event()

    def on_ready(port: int) -> None:
        bound.append(port)
        listening.set()

    worker = threading.Thread(target=lambda: server.run(ready=on_ready), daemon=True)
    worker.start()
    assert listening.wait(timeout=10), "server never started listening"
    return worker, bound[0]


def stop_running_server(server: DevServer, worker: threading.Thread) -> None:
    """Stop a server started by :func:`start_running_server` and wait for its thread."""
    server.stop()
    worker.join(timeout=10)
    assert not worker.is_alive()
