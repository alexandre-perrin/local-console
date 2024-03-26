import logging
from typing import Annotated

import trio
import typer
from wedge_cli.clients.agent import Agent

app = typer.Typer(help="Command to send RPC to a module instance")

logger = logging.getLogger(__name__)


@app.callback(invoke_without_command=True)
def rpc(
    instance_id: Annotated[
        str,
        typer.Argument(help="Target instance of the RPC"),
    ],
    method: Annotated[
        str,
        typer.Argument(help="Method of the RPC"),
    ],
    params: Annotated[
        str,
        typer.Argument(help="JSON representing the parameters"),
    ],
) -> None:
    try:
        trio.run(rpc_task, instance_id, method, params)
    except ConnectionError:
        raise SystemExit(f"Could not send command {method} to device {instance_id}")


async def rpc_task(instance_id: str, method: str, params: str) -> None:
    agent = Agent()  # type: ignore
    await agent.initialize_handshake()
    async with agent.mqtt_scope([]):
        await agent.rpc(instance_id, method, params)
