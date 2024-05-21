# Copyright 2024 Sony Semiconductor Solutions Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
import configparser
import json
import logging
import socket

from local_console.core.enums import config_paths
from local_console.core.schemas.schemas import IPAddress

logger = logging.getLogger(__name__)


class Listener:
    def __init__(self, ip: IPAddress, port: int) -> None:
        self.ip = ip.ip_value
        self.port = port
        self.config_paths = config_paths

    def open_listener(self) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        logger.info("Socket created")

        # managing error exception
        try:
            self.socket.bind((self.ip, int(self.port)))
        except OSError:
            logger.error("Bind failed")
            exit(1)
        logger.info("Connected")

    def receive_config(self) -> None:
        self.socket.listen()
        (self.conn, self.addr) = self.socket.accept()
        data: bytes = self.conn.recv(1024)  # preprocess config
        config_parse = configparser.ConfigParser()
        config_dict = json.loads(data.decode("utf-8").strip().replace("'", ""))
        for section_names, values in config_dict.items():
            if "host" in values.keys() and isinstance(values["host"], dict):
                values["host"] = values["host"]["ip_value"]
            config_parse[section_names] = values
        # save config_paths
        with open(self.config_paths.config_path, "w") as f:
            config_parse.write(f)

        # Sending reply
        self.conn.send(bytes("Config received and applied", "utf-8"))
        self.conn.close()  # Close connections
