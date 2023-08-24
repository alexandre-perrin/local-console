import logging
import os
import subprocess

from wedge_cli.clients.listener import Listener
from wedge_cli.utils.config import get_config
from wedge_cli.utils.enums import Config

logger = logging.getLogger(__name__)


def start(**kwargs: dict) -> None:
    if kwargs["remote"]:
        if not kwargs["ip"] or not kwargs["port"]:
            logger.error("Please specify an IP and a port")
            exit()
        server = Listener(ip=kwargs["ip"], port=kwargs["port"])  # type: ignore
        server.open_listener()
        server.recieve_config()

    try:
        config = get_config()
        env = os.environ.copy()
        env["EVP_IOT_PLATFORM"] = config["evp"]["iot-platform"]
        env["EVP_VERSION"] = config["evp"]["version"]
        env["EVP_MQTT_HOST"] = config["mqtt"]["host"]
        env["EVP_MQTT_PORT"] = config["mqtt"]["port"]
        env["EVP_DATA_DIR"] = str(Config.EVP_DATA)
        env["EVP_HTTPS_CA_CERT"] = str(Config.HTTPS_CA_PATH)
        env["EVP_REPORT_STATUS_INTERVAL_MAX_SEC"] = "3"
        # TODO: check process return code
        command = ["evp_agent"]
        if kwargs["library"]:
            libraries = []
            for l in kwargs["library"]:
                libraries.append("-l")
                libraries.append(l)
            command += libraries
        logger.debug(f"Running: {' '.join(command)}")
        subprocess.run(command, env=env)
    except FileNotFoundError:
        logger.warning("evp_agent not in PATH")
        exit(1)
