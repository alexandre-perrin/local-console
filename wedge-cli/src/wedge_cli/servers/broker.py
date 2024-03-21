import logging
import platform
import re
import subprocess
import sys
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

        cmd = [broker_bin, "-v", "-c", str(config_file)]
        invocation = partial(
            trio.run_process,
            command=cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        broker_proc = await nursery.start(invocation)
        # This is to check the broker start up.
        # A (minor) enhancement would be to poll the broker.
        while True:
            data = await broker_proc.stdout.receive_some()
            if data:
                data = data.decode("utf-8")
                logger.debug(data)
                pattern = re.compile(r"mosquitto version (\d+\.\d+\.\d+) running")
                if "Error" in data:
                    logger.error("Mosquitto already initialized")
                    sys.exit(1)
                elif pattern.search(data):
                    break
        yield broker_proc
        broker_proc.kill()


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
