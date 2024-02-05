import logging
import sys
import urllib.request
from pathlib import Path
from typing import Annotated

import typer
from wedge_cli.commands import build
from wedge_cli.commands import config
from wedge_cli.commands import deploy
from wedge_cli.commands import get
from wedge_cli.commands import logs
from wedge_cli.commands import new
from wedge_cli.commands import rpc
from wedge_cli.commands import start
from wedge_cli.utils.config import setup_default_config
from wedge_cli.utils.enums import config_paths
from wedge_cli.utils.logger import configure_logger

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="wedge_cli",
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)
app.add_typer(start.app, name="start")
app.add_typer(deploy.app, name="deploy")
app.add_typer(build.app, name="build")
app.add_typer(new.app, name="new")
app.add_typer(logs.app, name="logs")
app.add_typer(rpc.app, name="rpc")
app.add_typer(get.app, name="get")
app.add_typer(config.app, name="config")


def setup_agent_filesystem() -> None:
    evp_data = config_paths.evp_data_path
    if not evp_data.exists():
        logger.debug("Generating evp_data")
        evp_data.mkdir(parents=True, exist_ok=True)


def setup_default_https_ca() -> None:
    https_ca = config_paths.https_ca_path
    if https_ca.exists():
        return
    try:
        response = urllib.request.urlopen(config_paths.https_ca_url)
        with open(https_ca, "wb") as f:
            f.write(response.read())
        response.close()
    except Exception as e:
        logger.error("Error while downloading HTTPS CA", e)
        sys.exit(1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    config_dir: Annotated[
        Path,
        typer.Option(help="Path for the file configs of the CLI and agent"),
    ] = config_paths.home,
    debug: Annotated[
        bool, typer.Option("--debug", "-d", help="Set log level to debug")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Set log level to verbose")
    ] = False,
) -> None:
    config_paths.home = config_dir
    configure_logger(debug, verbose)
    setup_default_config()
    setup_agent_filesystem()
    setup_default_https_ca()

    ctx.obj = config_paths.config_path


if __name__ == "__main__":
    app()
