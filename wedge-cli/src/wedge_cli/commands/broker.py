import logging
from typing import Annotated

import trio
import typer
from wedge_cli.core.config import get_config
from wedge_cli.core.schemas import AgentConfiguration
from wedge_cli.servers.broker import spawn_broker

app = typer.Typer(help="Command to start a MQTT broker")

logger = logging.getLogger(__name__)


@app.callback(invoke_without_command=True)
def broker(
    server_name: Annotated[
        str,
        typer.Argument(
            help="Server name to assign for TLS server verification, if TLS is enabled"
        ),
    ] = "localhost",
) -> None:
    try:
        config = get_config()
        trio.run(broker_task, config, server_name)
    except KeyboardInterrupt:
        logger.warning("Cancelled by the user.")


async def broker_task(config: AgentConfiguration, server_name: str) -> None:
    logger.setLevel(logging.INFO)
    async with (
        trio.open_nursery() as nursery,
        spawn_broker(config, server_name, nursery),
    ):
        logger.info(f"MQTT broker listening on port {config.mqtt.port}")
        await trio.sleep_forever()
