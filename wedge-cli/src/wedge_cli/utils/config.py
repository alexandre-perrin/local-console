import configparser
import logging
from pathlib import Path

from wedge_cli.utils.enums import Config

logger = logging.getLogger(__name__)


def get_default_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config["evp"] = {
        "iot-platform": "tb",
        "version": "EVP2",
    }
    config["mqtt"] = {"host": "localhost", "port": "1883"}
    config["webserver"] = {"host": "localhost", "port": "8000"}
    return config


def setup_default_config() -> None:
    config_file = Path(Config.CONFIG_PATH)
    if not config_file.is_file():
        logger.info("Generating default config")
        try:
            config_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            logger.error(f"Error while generating folder {config_file.parent}")
            exit(1)
        with open(Config.CONFIG_PATH, "w") as f:
            get_default_config().write(f)


def get_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config.read(Config.CONFIG_PATH)
    return config
