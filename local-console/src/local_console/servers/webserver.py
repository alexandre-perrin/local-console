import http.server
import logging
import socketserver
import threading
from abc import ABC
from abc import abstractmethod
from collections.abc import Sequence
from pathlib import Path
from types import TracebackType
from typing import Any
from typing import Callable
from typing import Optional

logger = logging.getLogger(__name__)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(
        self, *args: Any, on_incoming: Optional[Callable] = None, **kwargs: Any
    ):
        self.on_incoming = on_incoming
        super().__init__(*args, **kwargs)

    def log_message(self, _format: str, *args: Sequence[str]) -> None:
        logger.debug(" ".join(str(arg) for arg in args))

    def do_PUT(self) -> None:
        try:
            content_length = int(self.headers["Content-Length"])
            data = self.rfile.read(content_length)
            dest_path = Path(self.directory) / self.path.lstrip("/")
            dest_path.write_bytes(data)
            self.send_response(200)
            self.end_headers()

            # Notify of new file via the queue
            if self.on_incoming:
                self.on_incoming(dest_path)

        except Exception as e:
            logger.warning(f"Error while receiving data: {e}")
            self.send_response(500)
            self.end_headers()

    do_POST = do_PUT


class GenericWebserver(ABC):
    """
    This class connects an HTTP server class such as the one
    defined above, with an HTTP handler class, into a convenient
    context manager. The handler class must be returned from
    the handler() method, to be implemented.
    """

    def __init__(self, port: int, deploy: bool = True) -> None:
        self.port = port
        self.deploy = deploy

    @abstractmethod
    def handler(self, *args: Any, **kwargs: Any) -> http.server.BaseHTTPRequestHandler:
        "Must return an specialization of BaseHTTPRequestHandler"

    def start(self) -> None:
        if self.deploy:
            # Create the server object
            self.server = ThreadedHTTPServer(("0.0.0.0", self.port), self.handler)

            # Start the server in a new thread
            self.thread = threading.Thread(target=self.server.serve_forever)
            self.thread.start()

            self.port = self.server.server_port
            logger.debug("Serving at port %d", self.port)

    def stop(self) -> None:
        if not self.deploy:
            return

        # Shutdown the server after exiting the context
        self.server.shutdown()
        self.server.server_close()

    def __enter__(self) -> "GenericWebserver":
        self.start()
        return self

    def __exit__(
        self,
        _exc_type: Optional[type[BaseException]],
        _exc_val: Optional[BaseException],
        _exc_tb: Optional[TracebackType],
    ) -> None:
        self.stop()


class SyncWebserver(GenericWebserver):
    """
    This class applies the generic webserver class above for providing
    the HTTP file server required in deployment workflows.
    """

    def __init__(
        self,
        directory: Path,
        port: int = 0,
        on_incoming: Optional[Callable] = None,
        deploy: bool = True,
    ) -> None:
        super().__init__(port, deploy)
        self.dir = directory
        self.on_incoming = on_incoming

    def handler(self, *args: Any, **kwargs: Any) -> CustomHTTPRequestHandler:
        return CustomHTTPRequestHandler(
            *args, on_incoming=self.on_incoming, directory=str(self.dir), **kwargs
        )


class AsyncWebserver(SyncWebserver):
    """
    This class wraps the synchronous context manager methods
    from SyncWebserver, as they are not really blocking. This
    enables managing the webserver from async contexts.
    """

    async def __aenter__(self) -> "GenericWebserver":
        return self.__enter__()

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        return self.__exit__(exc_type, exc_val, exc_tb)
