# Copyright 2024 Sony Semiconductor Solutions Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
import logging
import shutil
import signal
import sys
import urllib.request
from importlib.metadata import version
from pathlib import Path
from types import FrameType
from typing import Annotated
from typing import Optional

import typer
from local_console.commands import broker
from local_console.commands import build
from local_console.commands import config
from local_console.commands import deploy
from local_console.commands import get
from local_console.commands import gui
from local_console.commands import logs
from local_console.commands import new
from local_console.commands import qr
from local_console.commands import rpc
from local_console.commands import start
from local_console.core.config import setup_default_config
from local_console.core.enums import Config
from local_console.core.enums import config_paths
from local_console.utils.logger import configure_logger

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="local_console",
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
app.add_typer(broker.app, name="broker")
app.add_typer(gui.app, name="gui")
app.add_typer(qr.app, name="qr")


def handle_exit(signal: int, frame: Optional[FrameType]) -> None:
    raise SystemExit


signal.signal(signal.SIGTERM, handle_exit)


def setup_agent_filesystem() -> None:
    evp_data = config_paths.evp_data_path
    if not evp_data.exists():
        logger.debug("Generating evp_data")
        evp_data.mkdir(parents=True, exist_ok=True)


def setup_default_https_ca() -> None:
    default_config_home = Config()
    target_https_ca = config_paths.https_ca_path
    source_https_ca = default_config_home.https_ca_path

    assert target_https_ca.parent.is_dir()
    if not source_https_ca.parent.is_dir():
        source_https_ca.parent.mkdir(parents=True, exist_ok=True)

    if not source_https_ca.is_file():
        logger.debug("Downloading trusted CA bundle into cache")
        try:
            response = urllib.request.urlopen(config_paths.https_ca_url)
            with open(source_https_ca, "wb") as f:
                f.write(response.read())
            response.close()
        except Exception as e:
            logger.error(f"Error while downloading HTTPS CA: {e}")
            sys.exit(1)

    if not target_https_ca.is_file():
        logger.debug("Copying trusted CA bundle from cache")
        shutil.copy(source_https_ca, target_https_ca)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    config_dir: Annotated[
        Path,
        typer.Option(help="Path for the file configs of the CLI and agent"),
    ] = config_paths.home,
    silent: Annotated[
        bool,
        typer.Option(
            "--silent",
            "-s",
            help="Decrease log verbosity (only show warnings and errors)",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose", "-v", help="Increase log verbosity (show debug messages too)"
        ),
    ] = False,
) -> None:
    if not ctx.invoked_subcommand:
        print(ctx.get_help())
        return

    config_paths.home = config_dir
    configure_logger(silent, verbose)
    setup_default_config()
    setup_agent_filesystem()
    setup_default_https_ca()

    try:
        logger.info(f"Version: {version('local-console')}")
    except Exception as e:
        logger.warning(f"Error while getting version from Python package: {e}")

    ctx.obj = config_paths.config_path


if __name__ == "__main__":
    app()
