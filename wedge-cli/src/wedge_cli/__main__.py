import logging
import sys
import urllib.request
from pathlib import Path

from wedge_cli.commands.build import build
from wedge_cli.commands.config import config
from wedge_cli.commands.deploy import deploy
from wedge_cli.commands.get import get
from wedge_cli.commands.logs import logs
from wedge_cli.commands.new import new
from wedge_cli.commands.start import start
from wedge_cli.utils.config import setup_default_config
from wedge_cli.utils.enums import Command
from wedge_cli.utils.enums import Config
from wedge_cli.utils.logger import configure_logger
from wedge_cli.utils.parser import get_parser

logger = logging.getLogger(__name__)

COMMANDS = {
    Command.START: start,
    Command.DEPLOY: deploy,
    Command.GET: get,
    Command.CONFIG: config,
    Command.LOGS: logs,
    Command.BUILD: build,
    Command.NEW: new,
}


def setup_agent_filesystem() -> None:
    evp_data = Path(Config.EVP_DATA)
    if not evp_data.exists():
        logger.debug("Generating evp_data")
        evp_data.mkdir(parents=True, exist_ok=True)


def setup_default_https_ca() -> None:
    if Config.HTTPS_CA_PATH.exists():
        return
    try:
        response = urllib.request.urlopen(Config.HTTPS_CA_URL)
        with open(Config.HTTPS_CA_PATH, "wb") as f:
            f.write(response.read())
        response.close()
    except Exception as e:
        logger.error("Error while downloading HTTPS CA", e)
        sys.exit(1)


def main() -> None:
    parser = get_parser()
    if len(sys.argv) < 2:
        parser.print_usage()
    args = parser.parse_args()
    configure_logger(args.debug, args.verbose)
    setup_default_config()
    setup_agent_filesystem()
    setup_default_https_ca()
    if args.command in COMMANDS:
        COMMANDS[args.command](**vars(args))  # type: ignore


if __name__ == "__main__":
    main()
