import http.server
import logging
import socketserver
import threading
from collections.abc import Sequence
from pathlib import Path
from types import TracebackType
from typing import Optional

logger = logging.getLogger(__name__)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *args: Sequence[str]) -> None:
        request, code, size = args
        logger.debug("%s %s %s", request, code, size)


class SyncWebserver:
    """
    This class exposes the HTTP server classes defined above
    as a convenient context manager.
    """

    def __init__(self, directory: Path, port: int) -> None:
        self.dir = directory
        self.port = port

    def __enter__(self) -> None:
        # Create the server object
        handler = lambda *args, **kwargs: CustomHTTPRequestHandler(
            *args, directory=str(self.dir), **kwargs
        )
        self.server = ThreadedHTTPServer(("0.0.0.0", self.port), handler)

        # Start the server in a new thread
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        logger.debug("Serving at port %d", self.port)

    def __exit__(
        self,
        _exc_type: Optional[type[BaseException]],
        _exc_val: Optional[BaseException],
        _exc_tb: Optional[TracebackType],
    ) -> None:
        # Shutdown the server after exiting the context
        self.server.shutdown()
        self.server.server_close()
