import json
import logging
from pathlib import Path
from typing import Annotated
from typing import Optional

import typer
from wedge_cli.clients.agent import Agent
from wedge_cli.clients.webserver import _WebServer
from wedge_cli.utils.config import get_deployment_schema
from wedge_cli.utils.config import get_empty_deployment
from wedge_cli.utils.enums import config_paths
from wedge_cli.utils.enums import Target
from wedge_cli.utils.schemas import DeploymentManifest


logger = logging.getLogger(__name__)

app = typer.Typer(help="Command for deploying application to the agent")


def deploy_empty(agent: Agent) -> None:
    deployment = get_empty_deployment()
    agent.deploy(deployment=deployment)


def deploy_manifest(
    agent: Agent,
    deployment_manifest: DeploymentManifest,
    signed: bool,
    timeout: int,
    target: Optional[Target],
) -> None:
    bin_fp = Path(config_paths.bin)
    if not bin_fp.exists():
        logger.warning("bin folder does not exist")
        exit(1)

    webserver = _WebServer(agent)
    webserver.update_deployment_manifest(deployment_manifest, target, signed)  # type: ignore
    num_modules = len(deployment_manifest.deployment.modules.keys())
    webserver.start(num_modules, timeout)  # type: ignore
    agent.deploy(json.dumps(deployment_manifest.model_dump()))
    webserver.close()


@app.callback(invoke_without_command=True)
def deploy(
    empty: Annotated[
        bool,
        typer.Option(
            "-e",
            "--empty",
            help="Option to remove previous deployment with an empty one",
        ),
    ] = False,
    signed: Annotated[
        bool,
        typer.Option(
            "-s",
            "--signed",
            help="Option to deploy signed files(already built with the 'build' command)",
        ),
    ] = False,
    timeout: Annotated[
        int,
        typer.Option(
            "-t",
            "--timeout",
            help="Set timeout to wait for the modules to be downloaded by the agent",
        ),
    ] = 10,
    target: Annotated[
        Optional[Target],
        typer.Argument(
            help="Optional argument to specify which AoT compilation to deploy. If not defined it will deploy the plain WASM"
        ),
    ] = None,
) -> None:
    agent = Agent()
    if empty:
        deploy_empty(agent=agent)
        return

    deployment_manifest = get_deployment_schema()

    deploy_manifest(
        agent=agent,
        deployment_manifest=deployment_manifest,
        signed=signed,
        timeout=timeout,
        target=target,
    )
