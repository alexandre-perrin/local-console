import logging
from typing import Annotated

import trio
import typer
from local_console.core.config import get_config
from local_console.core.schemas.schemas import AgentConfiguration
from local_console.servers.broker import spawn_broker

app = typer.Typer(
    help="Command to start a MQTT broker. It will fail if there is already a broker listening in the port specified in config"
)

logger = logging.getLogger(__name__)


@app.callback(invoke_without_command=True)
def broker(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Starts the broker in verbose mode"),
    ] = False,
    server_name: Annotated[
        str,
        typer.Argument(
            help="Server name to assign for TLS server verification, if TLS is enabled"
        ),
    ] = "localhost",
) -> None:
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    try:
        config = get_config()
        trio.run(broker_task, config, verbose, server_name)
    except KeyboardInterrupt:
        logger.warning("Cancelled by the user")


async def broker_task(
    config: AgentConfiguration, verbose: bool, server_name: str
) -> None:
    logger.setLevel(logging.INFO)
    async with (
        trio.open_nursery() as nursery,
        spawn_broker(config, nursery, verbose, server_name),
    ):
        logger.info(f"MQTT broker listening on port {config.mqtt.port}")
        await trio.sleep_forever()
