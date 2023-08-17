import logging

from wedge_cli.utils.config import get_config
from wedge_cli.utils.enums import Config

logger = logging.getLogger(__name__)


def config_get(key: str, **kwargs: dict) -> None:
    config = get_config()
    config_str = ""
    if key is None:
        prechar = ""
        for section in config.sections():
            config_str += f"{prechar}[{section}]\n"
            prechar = "\n"
            for key, value in config.items(section):
                config_str += f"{key} = {value}\n"
    else:
        key_split = key.split(".")
        if len(key_split) == 1:
            sec = key_split[0]
            if sec not in config:
                log = f"Invalid config section. Valid ones are: {config.sections()}"
                logger.error(log)
                exit(1)
            for opt, val in config.items(sec):
                config_str += f"{opt} = {val}\n"
        elif len(key_split) == 2:
            sec, opt = key_split
            val = config.get(sec, opt)
            config_str += f"{val}\n"
        else:
            logger.error("Incorrect selection. Filter using '<section>.<item>'")
            exit(1)

    print(config_str, end="")


def config_set(entry: str, **kwargs: dict) -> None:
    config = get_config()
    entry = entry[0]
    identifier, value = entry.split("=")
    section, option = identifier.split(".")

    if section not in config:
        log = f"Invalid config section. Valid ones are: {config.sections()}"
        logger.error(log)
        exit(1)
    if option not in config[section]:
        log = "Invalid config option"
        logger.error(log)
        exit(1)

    config[section][option] = value

    with open(Config.CONFIG_PATH, "w") as f:
        config.write(f)


def config(**kwargs: dict) -> None:  # type: ignore
    {
        "get": config_get,  # type: ignore
        "set": config_set,  # type: ignore
    }[
        str(kwargs["config_subparsers"])
    ](**kwargs)
