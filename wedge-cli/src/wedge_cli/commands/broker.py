import logging

import trio
import typer
from wedge_cli.core.config import get_config
from wedge_cli.core.schemas import AgentConfiguration
from wedge_cli.servers.broker import spawn_broker

app = typer.Typer(help="Command to start a MQTT broker")

logger = logging.getLogger(__name__)


@app.callback(invoke_without_command=True)
def broker() -> None:
    try:
        config = get_config()
        if not config.is_tls_enabled:
            trio.run(broker_task, config)
        else:
            logger.error("TLS mode not supported. Aborting.")
    except KeyboardInterrupt:
        logger.warning("Cancelled by the user.")


async def broker_task(config: AgentConfiguration) -> None:
    logger.setLevel(logging.INFO)
    async with (
        trio.open_nursery() as nursery,
        spawn_broker(config, nursery),
    ):
        logger.info(f"MQTT broker listening on port {config.mqtt.port}")
        await trio.sleep_forever()
