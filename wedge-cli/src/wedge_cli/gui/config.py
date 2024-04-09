import logging
from pathlib import Path
from typing import Optional

from kivy.config import Config

logger = logging.getLogger(__name__)

CONFIG_PATH = str(Path(__file__).parent / "assets/config.ini")


def configure() -> None:
    if Path(CONFIG_PATH).is_file():
        Config.read(CONFIG_PATH)
    else:
        logger.warning("Error while reading configuration file")


def resource_path(relative_path: str) -> Optional[str]:
    base_path = Path(__file__).parent
    logger.warning(f"base_path is {base_path}")
    target = base_path.joinpath(relative_path).resolve()
    if target.is_file():
        return str(target)
    return None
