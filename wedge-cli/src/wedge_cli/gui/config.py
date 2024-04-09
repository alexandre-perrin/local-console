import logging
from pathlib import Path
from kivy.config import Config

logger = logging.getLogger(__name__)

CONFIG_PATH = str(Path(__file__).parent / "assets/config.ini")

def configure() -> None:
    if Path(CONFIG_PATH).is_file():
        Config.read(CONFIG_PATH)
    else:
        logger.warning("Error while reading configuration file")
