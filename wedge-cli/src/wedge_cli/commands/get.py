import json
import logging
from typing import Annotated
from typing import Callable

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
    agent.read_only_loop(
        subs_topics=[MQTTTopics.TELEMETRY.value],
        message_task=on_message_telemetry,
    )


async def on_message_telemetry(cs: trio.CancelScope, agent: Agent) -> None:
    assert agent.client is not None
    async with agent.client.messages() as mgen:
        async for msg in mgen:
            payload = json.loads(msg.payload.decode())
            if payload:
                to_print = {
                    key: val for key, val in payload.items() if "device/log" not in key
                }
                print(to_print, flush=True)


@app.command(help="Get the status of instance")
def instance(
    instance_id: Annotated[
        str,
        typer.Argument(help="Target instance of the RPC."),
    ]
) -> None:
    agent = Agent()
    agent.read_only_loop(
        subs_topics=[MQTTTopics.ATTRIBUTES.value],
        message_task=on_message_instance(instance_id),
    )


def on_message_instance(instance_id: str) -> Callable:
    async def __task(cs: trio.CancelScope, agent: Agent) -> None:
        assert agent.client is not None
        async with agent.client.messages() as mgen:
            async for msg in mgen:
                payload = json.loads(msg.payload.decode())
                if (
                    "deploymentStatus" not in payload
                    or "instances" not in payload["deploymentStatus"]
                ):
                    continue

                instances = payload["deploymentStatus"]["instances"]
                if instance_id in instances.keys():
                    print(instances[instance_id])
                else:
                    logger.warning(
                        f"Module instance not found. The available module instances are {list(instances.keys())}"
                    )
                    cs.cancel()

    return __task
