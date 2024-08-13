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
from typing import Annotated

import trio
import typer
from exceptiongroup import ExceptionGroup
from local_console.core.config import config_obj
from local_console.core.schemas.schemas import DeviceConnection
from local_console.plugin import PluginBase
from local_console.servers.broker import BrokerException
from local_console.servers.broker import spawn_broker
from trio import open_nursery
from trio import sleep_forever

app = typer.Typer()

logger = logging.getLogger(__name__)


@app.command(
    help="Command to start a MQTT broker. It will fail if there is already a broker listening in the port specified in config"
)
def broker(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Starts the broker in verbose mode"),
    ] = False,
) -> None:
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    device_config = config_obj.get_active_device_config()
    trio.run(broker_task, device_config, verbose)


async def broker_task(config: DeviceConnection, verbose: bool) -> None:
    logger.setLevel(logging.INFO)
    try:
        async with (
            open_nursery() as nursery,
            spawn_broker(config.mqtt.port, nursery, verbose),
        ):
            try:
                logger.info(f"MQTT broker listening on port {config.mqtt.port}")
                await sleep_forever()
            except KeyboardInterrupt:
                logger.warning("Cancelled by the user")

    except ExceptionGroup as exc_grp:
        for e in exc_grp.exceptions:
            if isinstance(e, BrokerException):
                logger.error(" ".join(str(e).splitlines()))
                raise typer.Exit(1)


class BrokerCommand(PluginBase):
    implementer = app
