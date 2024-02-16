import logging
import platform
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from string import Template
from tempfile import TemporaryDirectory

import trio
from wedge_cli.core.enums import config_paths
from wedge_cli.core.schemas import AgentConfiguration

logger = logging.getLogger(__name__)

broker_assets = Path(__file__).parents[1] / "assets" / "broker"


@asynccontextmanager
async def spawn_broker(
    config: AgentConfiguration, nursery: trio.Nursery
) -> AsyncIterator[None]:

    with TemporaryDirectory() as tmp_dir:
        broker_bin = broker_assets / platform.system() / f"rumqttd{exe_ext()}"

        config_file = Path(tmp_dir) / "broker.toml"
        populate_broker_conf(config, config_file)

        cmd = [str(broker_bin.resolve()), "--config", str(config_file)]
        invocation = partial(trio.run_process, command=cmd)
        broker_proc = await nursery.start(invocation)
        yield broker_proc
        broker_proc.kill()


def exe_ext() -> str:
    return ".exe" if platform.system() == "Windows" else ""


def populate_broker_conf(config: AgentConfiguration, config_file: Path) -> None:
    data = {"mqtt_port": str(config.mqtt.port)}
    template_file = broker_assets / f"config.no-tls.toml.tpl"
    template = Template(template_file.read_text())
    rendered = template.substitute(data)
    config_file.write_text(rendered)
