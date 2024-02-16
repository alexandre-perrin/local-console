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
        logger.debug(" ".join(str(arg) for arg in args))

    def do_PUT(self) -> None:
        content_length = int(self.headers["Content-Length"])
        data = self.rfile.read(content_length)
        dest_path = Path(self.directory) / self.path.lstrip("/")
        dest_path.write_bytes(data)

        self.send_response(200)
        self.end_headers()

    do_POST = do_PUT


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


class AsyncWebserver(SyncWebserver):
    """
    This class wraps the synchronous context manager methods
    from SyncWebserver, as they are not really blocking. This
    enables managing the webserver from async contexts.
    """

    async def __aenter__(self) -> None:
        return self.__enter__()

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        return self.__exit__(exc_type, exc_val, exc_tb)
