import configparser
import json
import logging
import socket

from wedge_cli.utils.enums import Config

logger = logging.getLogger(__name__)


class Listener:
    def __init__(self, ip: str, port: int) -> None:
        self.ip = ip
        self.port = port

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

    def recieve_config(self) -> None:
        self.socket.listen()
        (self.conn, self.addr) = self.socket.accept()
        data: bytes = self.conn.recv(1024)
        # preprocess config
        config = configparser.ConfigParser()
        config_dict = json.loads(data.decode("utf-8"))
        for section in config_dict.keys():
            config.add_section(section)
            for key in config_dict[section].keys():
                config.set(section, key, config_dict[section][key])
        # save config
        with open(Config.CONFIG_PATH, "w") as f:
            config.write(f)

        # Sending reply
        self.conn.send(bytes("Config recieved and applied", "utf-8"))
        self.conn.close()  # Close connections
