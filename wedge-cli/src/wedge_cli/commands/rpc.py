import logging
from typing import Annotated

import typer
from wedge_cli.clients.agent import Agent

app = typer.Typer(help="Command to send RPC to module instance")

logger = logging.getLogger(__name__)


@app.callback(invoke_without_command=True)
def rpc(
    instance_id: Annotated[
        str,
        typer.Argument(help="Target instance of the RPC."),
    ],
    method: Annotated[
        str,
        typer.Argument(help="Method of the RPC."),
    ],
    params: Annotated[
        str,
        typer.Argument(help="JSON representing the parameters."),
    ],
) -> None:
    agent = Agent()  # type: ignore
    try:
        agent.rpc(instance_id, method, params)
    except ConnectionError:
        exit(1)
