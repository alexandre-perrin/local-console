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
import json
import logging
from typing import Annotated
from typing import Optional

import trio
import typer
from local_console.clients.agent import Agent
from local_console.core.config import config_obj
from local_console.core.schemas.schemas import DesiredDeviceConfig
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.plugin import PluginBase
from pydantic import ValidationError
from pydantic.json import pydantic_encoder

logger = logging.getLogger(__name__)
app = typer.Typer(
    help="Command to get or set configuration parameters of a camera or a module instance"
)


@app.command(
    "get", help="Gets the values for the requested config key, or the whole config"
)
def config_get(
    section: Annotated[
        Optional[str],
        typer.Argument(
            help="Section to be retrieved. If none specified, returns the whole config. Hierarchy is expressed with separation of a dot. E.g., evp.iot_platform"
        ),
    ] = None,
    device: Annotated[
        Optional[str],
        typer.Option(
            "--device",
            "-d",
            help="Device from which values are modified",
        ),
    ] = None,
) -> None:
    config = (
        config_obj.get_config() if not device else config_obj.get_device_config(device)
    )

    selected_config = config

    if section:
        sections_split = section.split(".")
        for parameter in sections_split:
            selected_config = getattr(selected_config, parameter)

    print(json.dumps(selected_config, indent=2, default=pydantic_encoder))


def _set(section: str, new: str | None, device: str | None) -> None:
    config = (
        config_obj.get_config() if not device else config_obj.get_device_config(device)
    )
    selected_config = config

    sections_split = section.split(".")
    for parameter in sections_split[:-1]:
        selected_config = getattr(selected_config, parameter)

    try:
        setattr(selected_config.model_copy(deep=True), sections_split[-1], new)
        config.model_copy(deep=True).__class__(**json.loads(config.model_dump_json()))
    except ValidationError as e:
        raise SystemExit(f"Error setting '{section}'. {e.errors()[0]['msg']}.")
    setattr(selected_config, sections_split[-1], new)
    config_obj.save_config()


@app.command("set", help="Sets the config key values to the specified value")
def config_set(
    section: Annotated[
        str,
        typer.Argument(
            help="Section of the configuration to be set. Hierarchy is expressed with separation of a dot. E.g., evp.iot_platform"
        ),
    ],
    new: Annotated[
        str,
        typer.Argument(
            help="New value to be used in the specified parameter of the section"
        ),
    ],
    device: Annotated[
        Optional[str],
        typer.Option(
            "--device",
            "-d",
            help="Device from which values are modified",
        ),
    ] = None,
) -> None:
    _set(section, new, device)


@app.command("unset", help="Removes the value of a nullable configuration key")
def config_unset(
    section: Annotated[
        str,
        typer.Argument(
            help="Section of the configuration to be set. Hierarchy is expressed with separation of a dot."
        ),
    ],
    device: Annotated[
        Optional[str],
        typer.Option(
            "--device",
            "-d",
            help="Device from which values are modified",
        ),
    ] = None,
) -> None:
    _set(section, None, device)


@app.command("instance", help="Configure an application module instance")
def config_instance(
    instance_id: Annotated[
        str,
        typer.Argument(help="Target instance of the configuration"),
    ],
    topic: Annotated[
        str,
        typer.Argument(help="Topic of the configuration"),
    ],
    config: Annotated[
        str,
        typer.Argument(help="Data of the configuration"),
    ],
) -> None:
    try:
        trio.run(configure_task, instance_id, topic, config)
    except ConnectionError:
        raise SystemExit(
            f"Connection error while attempting to set configuration topic '{topic}' for instance {instance_id}"
        )


async def configure_task(instance_id: str, topic: str, cfg: str) -> None:
    config = config_obj.get_config()
    config_device = config_obj.get_active_device_config()
    schema = OnWireProtocol.from_iot_spec(config.evp.iot_platform)
    agent = Agent(config_device.mqtt.host, config_device.mqtt.port, schema)
    await agent.initialize_handshake()
    async with agent.mqtt_scope([]):
        await agent.configure(instance_id, topic, cfg)


@app.command("device", help="Configure the device")
def config_device(
    interval_max: Annotated[
        int,
        typer.Argument(help="Max interval to report"),
    ],
    interval_min: Annotated[
        int,
        typer.Argument(help="Min interval to report"),
    ],
) -> None:
    retcode = 1
    try:
        desired_device_config = DesiredDeviceConfig(
            reportStatusIntervalMax=interval_max, reportStatusIntervalMin=interval_min
        )
        retcode = trio.run(config_device_task, desired_device_config)
    except ValueError:
        logger.warning("Report status interval out of range.")
    except ConnectionError:
        raise SystemExit(
            "Connection error while attempting to set device configuration"
        )
    raise typer.Exit(code=retcode)


async def config_device_task(desired_device_config: DesiredDeviceConfig) -> int:
    retcode = 1
    config = config_obj.get_config()
    config_device = config_obj.get_active_device_config()
    schema = OnWireProtocol.from_iot_spec(config.evp.iot_platform)
    agent = Agent(config_device.mqtt.host, config_device.mqtt.port, schema)
    if schema == OnWireProtocol.EVP2:
        async with agent.mqtt_scope([]):
            await agent.device_configure(desired_device_config)
        retcode = 0
    else:
        logger.warning(f"Unsupported on-wire schema {schema} for this command.")
    return retcode


class ConfigCommand(PluginBase):
    implementer = app
