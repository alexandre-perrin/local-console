import json
import logging
import socket
from typing import Optional

from wedge_cli.utils.config import get_config
from wedge_cli.utils.config import get_default_config
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
            if opt in config[sec]:
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


def config_send(entries: Optional[list[str]], **kwargs: dict) -> None:
    config = get_default_config()
    if entries:
        for entry in entries:
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

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((kwargs["ip"], int(kwargs["port"])))  # type: ignore
    config_dict: dict = {}
    for section in config.sections():
        config_dict[section] = {}
        for option in config.options(section):
            config_dict[section][option] = config.get(section, option)
    s.send(bytes(json.dumps(config_dict), "utf-8"))

    while True:
        reply = s.recv(1024)
        if not reply:
            continue
        elif reply:
            logger.info(reply.decode("utf-8"))
            break


def config(**kwargs: dict) -> None:
    command = str(kwargs["config_subparsers"])
    {
        "get": config_get,  # type: ignore
        "set": config_set,  # type: ignore
        "send": config_send,  # type: ignore
    }[command](**kwargs)
