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
from wedge_cli.utils.tls import ensure_certificate_pair_exists

logger = logging.getLogger(__name__)

broker_assets = Path(__file__).parents[1] / "assets" / "broker"


@asynccontextmanager
async def spawn_broker(
    config: AgentConfiguration, nursery: trio.Nursery, verbose: bool, server_name: str
) -> AsyncIterator[trio.Process]:
    if config.is_tls_enabled:
        broker_cert_path, broker_key_path = config_paths.broker_cert_pair
        ensure_certificate_pair_exists(
            server_name, broker_cert_path, broker_key_path, config.tls, is_server=True
        )

    with TemporaryDirectory() as tmp_dir:
        if platform.system() == "Linux":
            broker_bin = "mosquitto"
        elif platform.system() == "Windows":
            broker_bin = "C:\\Program Files\\mosquitto\\mosquitto.exe"

        config_file = Path(tmp_dir) / "broker.toml"
        populate_broker_conf(config, config_file)

        cmd = [broker_bin, *(("-v",) if verbose else ()), "-c", str(config_file)]
        invocation = partial(trio.run_process, command=cmd)

        broker_proc = await nursery.start(invocation)
        # This is a margin to let the broker start up.
        # A (minor) enhancement would be to poll the broker.
        await trio.sleep(2)
        yield broker_proc
        broker_proc.kill()


def exe_ext() -> str:
    return ".exe" if platform.system() == "Windows" else ""


def populate_broker_conf(config: AgentConfiguration, config_file: Path) -> None:
    data = {"mqtt_port": str(config.mqtt.port)}

    if config.is_tls_enabled:
        broker_cert_path, broker_key_path = config_paths.broker_cert_pair
        variant = "tls"
        data.update(
            {
                "ca_crt": str(config.tls.ca_certificate),
                "server_crt": str(broker_cert_path),
                "server_key": str(broker_key_path),
            }
        )
    else:
        variant = "no-tls"

    logger.info(f"MQTT broker in {variant} mode")
    template_file = broker_assets / f"config.{variant}.toml.tpl"
    template = Template(template_file.read_text())
    rendered = template.substitute(data)
    config_file.write_text(rendered)
