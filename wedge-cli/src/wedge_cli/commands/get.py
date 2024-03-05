import json
import logging
from typing import Annotated

import trio
import typer
from wedge_cli.clients.agent import Agent
from wedge_cli.core.camera import MQTTTopics

logger = logging.getLogger(__name__)

app = typer.Typer(
    name="get", help="Command to get information of the running sensing application"
)


@app.command(help="Get the status of deployment")
def deployment() -> None:
    agent = Agent()
    agent.read_only_loop(
        subs_topics=[MQTTTopics.ATTRIBUTES.value],
        message_task=on_message_print_payload,
    )


async def on_message_print_payload(cs: trio.CancelScope, agent: Agent) -> None:
    assert agent.client is not None
    async with agent.client.messages() as mgen:
        async for msg in mgen:
            payload = json.loads(msg.payload.decode())
            if payload:
                print(payload, flush=True)
            else:
                logger.debug("Empty message arrived")


@app.command(help="Get the telemetries")
def telemetry() -> None:
    agent = Agent()
    agent.get_telemetry()


@app.command(help="Get the status of instance")
def instance(
    instance_id: Annotated[
        str,
        typer.Argument(help="Target instance of the RPC."),
    ]
) -> None:
    agent = Agent()
    agent.get_instance(instance_id)
