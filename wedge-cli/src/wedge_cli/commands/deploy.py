import json
import logging
import os
import select
import socket
import threading
import time
from pathlib import Path

from wedge_cli.clients.agent import agent

logger = logging.getLogger(__name__)


class _WebServer:
    def __init__(self, port: int = 8000):
        self.host = "localhost"
        self.port = port
        self.stop_flag = threading.Event()

    def start(self, num_downloads: int) -> None:
        self.web_server_thread = threading.Thread(
            target=lambda: self._start_http_server(num_downloads), daemon=True
        )
        self.web_server_thread.start()

    def close(self) -> None:
        self.stop_flag.set()
        self.web_server_thread.join()

    def _start_http_server(self, num_downloads: int, timeout: int = 5) -> None:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen()

        inputs = [server_socket]
        tstart = time.time()
        # TODO: use `reconcileStatus` instead of num_downloads
        while num_downloads != 0 and (available_time := time.time() - tstart < timeout):
            readable, _, _ = select.select(inputs, [], [], 1)
            for sock in readable:
                if sock is server_socket:
                    client_socket, client_address = server_socket.accept()
                    inputs.append(client_socket)
                else:
                    module = self.handle_request(sock)
                    if module is not None:
                        logger.info(f"Downloaded module {module}")
                    num_downloads -= 1
                    inputs.remove(sock)
                    sock.close()

        if not available_time:
            logger.warning("Timeout when sending modules.")

        server_socket.close()

    def handle_request(self, client_socket) -> str | None:  # type: ignore
        module = None

        bufsize = 4096
        data = client_socket.recv(bufsize)
        if len(data) == bufsize:
            logger.error("HTTP request data too large")
            exit(1)

        request = data.decode("utf-8")
        request_parts = request.split()

        # https://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5
        if len(request_parts) >= 3:
            method, request_uri = request_parts[:2]
            if method != "GET":
                logger.warning("Wrong HTTP method to webserver:", method)

            url_path = request_uri[1:]  # Remove leading slash
            file_path = Path(url_path)
            if file_path == "":
                response = b"HTTP/1.1 200 OK\r\n"
                response += b"Content-type: text/html\r\n"
                response += b"\r\n"
                response += self.get_directory_listing().encode("utf-8")
            elif file_path.exists():
                with open(file_path, "rb") as file:
                    response = b"HTTP/1.1 200 OK\r\n"
                    response += b"\r\n"
                    response += file.read()
                module = file_path
            else:
                response = b"HTTP/1.1 404 Not Found\r\n"
                response += b"\r\n"
                response += b"File not found"
        else:
            logger.error("Invalid HTTP request line")
            response = b"HTTP/1.1 400 Bad Request\r\n"
            response += b"\r\n"
            response += b"Bad request"

        client_socket.sendall(response)
        client_socket.close()
        return str(module)

    @staticmethod
    def get_directory_listing() -> str:
        files = os.listdir(".")
        listing = "<html><body><ul>"
        for file in files:
            listing += f'<li><a href="{file}">{file}</a></li>'
        listing += "</ul></body></html>"
        return listing


def deploy(**kwargs: dict) -> None:
    bin_fp = Path("bin")
    if not bin_fp.exists():
        logger.warning("Folder bin does not exists")
        exit(1)

    deployment_fp = Path("deployment.json")
    if not deployment_fp.exists():
        logger.warning("File deployment.json does not exists")
        exit(1)

    with open(deployment_fp, "rb") as f:
        deployment = json.load(f)
    with open(deployment_fp, "w") as f:
        json.dump(deployment, f, indent=4)

    num_modules = len(deployment["deployment"]["modules"])

    webserver = _WebServer()
    webserver.start(num_modules)
    agent.deploy(str(deployment_fp))
    webserver.close()
