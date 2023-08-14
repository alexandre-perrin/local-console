import configparser
import logging
from pathlib import Path

from wedge_cli.utils.enums import Config
from wedge_cli.utils.logger import configure_logger
from wedge_cli.utils.parser import get_parser

logger = logging.getLogger(__name__)


def get_default_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config["evp"] = {
        "iot-platform": "tb",
        "version": "EVP2",
    }
    config["mqtt"] = {"host": "localhost", "port": "1883"}
    return config


def setup_default_config() -> None:
    if not Path(Config.CONFIG_PATH).is_file():
        logger.info("Generating default config")
        with open(Config.CONFIG_PATH, "w") as f:
            get_default_config().write(f)


def setup_agent_filesystem() -> None:
    evp_data = Path(Config.EVP_DATA)
    if not evp_data.exists():
        logger.debug("Generating evp_data")
        evp_data.mkdir(parents=True, exist_ok=True)


def main() -> None:
    args = get_parser()
    configure_logger(args.debug, args.verbose)
    setup_default_config()
    setup_agent_filesystem()


if __name__ == "__main__":
    main()
