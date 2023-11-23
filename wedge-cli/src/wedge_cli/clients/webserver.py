import hashlib
import json
import logging
import os
import select
import socket
import threading
import time
from pathlib import Path
from typing import Optional

from wedge_cli.clients.agent import Agent
from wedge_cli.utils.config import get_config
from wedge_cli.utils.enums import config_paths
from wedge_cli.utils.enums import ModuleExtension
from wedge_cli.utils.enums import Target
from wedge_cli.utils.schemas import AgentConfiguration
from wedge_cli.utils.schemas import DeploymentManifest


logger = logging.getLogger(__name__)


def _calculate_sha256(filename: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(filename, "rb") as f:
        sha256_hash.update(f.read())
    return sha256_hash.hexdigest()


class _WebServer:
    def __init__(self, agent: Agent):
        config: AgentConfiguration = get_config()  # type:ignore
        self.host = config.webserver.host.ip_value
        self.port = config.webserver.port
        self.stop_flag = threading.Event()
        self.agent = agent

    def start(self, num_downloads: int, timeout: int) -> None:
        self.web_server_thread = threading.Thread(
            target=lambda: self._start_http_server(num_downloads, timeout), daemon=True
        )
        self.web_server_thread.start()

    def close(self) -> None:
        self.stop_flag.set()
        self.web_server_thread.join()

    def _start_http_server(self, num_downloads: int, timeout: int) -> None:
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

    def handle_request(self, client_socket: socket.socket) -> Optional[str]:
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
                logger.error(f"File {file_path} not found")
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

    def update_deployment_manifest(
        self,
        deployment_manifest: DeploymentManifest,
        target_arch: Optional[Target],
        use_signed: bool,
    ) -> None:
        agent_config: AgentConfiguration = get_config()  # type: ignore
        files = set(os.listdir("bin"))
        for module in deployment_manifest.deployment.modules.keys():
            wasm_file = f"{module}.{ModuleExtension.WASM}"
            if wasm_file not in files:
                logger.error(
                    f"{wasm_file} not found. Please build the modules before deployment"
                )
                exit(1)

            file = wasm_file
            if target_arch:
                file = f"{module}.{target_arch}.{ModuleExtension.AOT}"
                if use_signed:
                    file = f"{file}.{ModuleExtension.SIGNED}"
            else:
                if use_signed:
                    logger.warning(
                        f"There is no target architecture, the {file} module to be deployed is not signed"
                    )
            deployment_manifest.deployment.modules[module].hash = _calculate_sha256(
                str(Path("bin") / file)
            )
            deployment_manifest.deployment.modules[
                module
            ].downloadUrl = f"http://{agent_config.webserver.host.ip_value}:{agent_config.webserver.port}/bin/{file}"

        with open(config_paths.deployment_json, "w") as f:
            json.dump(deployment_manifest.model_dump(), f, indent=2)
