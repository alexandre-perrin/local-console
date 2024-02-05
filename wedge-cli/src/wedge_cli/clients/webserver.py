import http.server
import logging
import socketserver
import threading
from collections.abc import Iterator
from collections.abc import Sequence
from contextlib import contextmanager
from pathlib import Path


logger = logging.getLogger(__name__)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *args: Sequence[str]) -> None:
        request, code, size = args
        logger.debug("%s %s %s", request, code, size)


@contextmanager
def run_server(directory: Path, port: int) -> Iterator[None]:
    # Create the server object
    handler = lambda *args, **kwargs: CustomHTTPRequestHandler(
        *args, directory=str(directory), **kwargs
    )
    server = ThreadedHTTPServer(("0.0.0.0", port), handler)

    # Start the server in a new thread
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    logger.debug("Serving at port %d", port)
    try:
        yield
    finally:
        # Shutdown the server after exiting the context
        server.shutdown()
        server.server_close()
