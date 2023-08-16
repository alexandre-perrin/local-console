import logging
import os
import subprocess

from wedge_cli.utils.config import get_config
from wedge_cli.utils.enums import Config

logger = logging.getLogger(__name__)


def start(**kwargs: dict) -> None:
    try:
        config = get_config()
        env = os.environ.copy()
        env["EVP_IOT_PLATFORM"] = config["evp"]["iot-platform"]
        env["EVP_VERSION"] = config["evp"]["version"]
        env["EVP_MQTT_HOST"] = config["mqtt"]["host"]
        env["EVP_MQTT_PORT"] = config["mqtt"]["port"]
        env["EVP_DATA_DIR"] = str(Config.EVP_DATA)
        # TODO: check process return code
        subprocess.run(["evp_agent"], env=env)
    except FileNotFoundError:
        logger.warning("evp_agent not in PATH")
        exit(1)
