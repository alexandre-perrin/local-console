# Copyright 2024 Sony Semiconductor Solutions Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
import logging
import re
import subprocess
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from shutil import which
from string import Template
from tempfile import TemporaryDirectory

import trio
from trio import run_process

logger = logging.getLogger(__name__)

broker_assets = Path(__file__).parents[1] / "assets" / "broker"


class BrokerException(Exception):
    """
    Class for broker management exceptions
    """


@asynccontextmanager
async def spawn_broker(
    port: int, nursery: trio.Nursery, verbose: bool
) -> AsyncIterator[trio.Process]:

    broker_bin = which("mosquitto")
    if not broker_bin:
        raise ValueError(
            "Could not find mosquitto in the PATH. Please add it and try again"
        )

    with TemporaryDirectory() as tmp_dir:
        config_file = Path(tmp_dir) / "broker.toml"
        populate_broker_conf(port, config_file)

        cmd = [broker_bin, "-v", "-c", str(config_file)]
        invocation = partial(
            run_process,
            command=cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        broker_proc = await nursery.start(invocation)
        # This is to check the broker start up.
        # A (minor) enhancement would be to poll the broker.
        pattern = re.compile(r"mosquitto version (\d+\.\d+\.\d+) running")
        while True:
            data = await broker_proc.stdout.receive_some()
            if data:
                data = data.decode("utf-8")
                for line in data.splitlines():
                    logger.debug(line)

                if "error" in data.lower():
                    line = next(
                        line for line in data.splitlines() if "error" in line.lower()
                    )
                    raise BrokerException(
                        f"{line} (On port {port}).\nPlease check and restart Local Console."
                    )
                elif pattern.search(data):
                    break

        nursery.start_soon(get_broker_logs, broker_proc.stdout)
        yield broker_proc
        broker_proc.kill()


def populate_broker_conf(port: int, config_file: Path) -> None:
    data = {"mqtt_port": str(port)}
    variant = "no-tls"
    logger.info(f"MQTT broker in {variant} mode")
    template_file = broker_assets / f"config.{variant}.toml.tpl"
    template = Template(template_file.read_text())
    rendered = template.substitute(data)
    config_file.write_text(rendered)


async def get_broker_logs(proc_stdout: trio.abc.ReceiveStream) -> None:
    async for chunk in proc_stdout:
        for line in chunk.decode().splitlines():
            logger.debug(line)
