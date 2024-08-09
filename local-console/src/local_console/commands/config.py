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
from typing import Any
from typing import Optional

import trio
import typer
from local_console.clients.agent import Agent
from local_console.core.config import config_obj
from local_console.core.config import ConfigError
from local_console.core.schemas.schemas import DesiredDeviceConfig
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.plugin import PluginBase
from pydantic import ValidationError
from pydantic.json import pydantic_encoder

logger = logging.getLogger(__name__)
app = typer.Typer(help="Configure devices, module instances, and Local Console")


@app.command(
    "get",
    help="Retrieve the value of a specific config key or display the entire configuration",
)
def config_get(
    ctx: typer.Context,
    section: Annotated[
        Optional[str],
        typer.Argument(
            help="Section of the configuration to retrieve. If not specified, the entire configuration is returned. "
            "Use dot notation to navigate through hierarchical sections, e.g., `evp.iot_platform`. "
            "For device-specific configurations, use the `--device` option."
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
    try:
        config = (
            config_obj.get_config()
            if not device
            else config_obj.get_device_config_by_name(device)
        )

        selected_config = config

        if section:
            sections_split = section.split(".")
            for parameter in sections_split:
                selected_config = getattr(selected_config, parameter)

        print(json.dumps(selected_config, indent=2, default=pydantic_encoder))

    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        raise typer.Exit(1)


def _set(section: str, new: str | None, device: str | None) -> None:
    if section.startswith("evp."):
        __set_evp(section, new, device)
    else:
        __set_device_scope(section, new, device)


def __set_device_scope(section: str, new: str | None, device: str | None) -> None:
    assert not section.startswith("evp.")

    device_config = (
        config_obj.get_active_device_config()
        if not device
        else config_obj.get_device_config_by_name(device)
    )

    selected_config = device_config
    sections_split = section.split(".")
    for parameter in sections_split[:-1]:
        selected_config = getattr(selected_config, parameter)

    parameter = sections_split[-1]
    if new is not None:
        new_val: Any = new if parameter != "port" else int(new)
    else:
        new_val = None

    try:
        setattr(selected_config, parameter, new_val)

        # Ensure consistency of the active device pointer
        if len(config_obj.config.devices) == 1:
            config_obj.config.active_device = device_config.mqtt.port

        config_obj.save_config()
    except ValidationError as e:
        raise SystemExit(f"Error setting '{section}'. {e.errors()[0]['msg']}.")


def __set_evp(section: str, new: str | None, device: str | None) -> None:
    assert section.startswith("evp.")

    sections_split = section.split(".")
    selected_config = config_obj.config
    for parameter in sections_split[:-1]:
        selected_config = getattr(selected_config, parameter)

    try:
        setattr(selected_config, sections_split[-1], new)
        config_obj.save_config()
    except ValidationError as e:
        raise SystemExit(f"Error setting '{section}'. {e.errors()[0]['msg']}.")


@app.command("set", help="Sets the configuration key to the specified value")
def config_set(
    section: Annotated[
        str,
        typer.Argument(
            help="Section of the configuration to be modified. Use dot notation to express hierarchy, e.g., `evp.iot_platform`"
            "For device-specific configurations, use the `--device` option."
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
            help="Section of the configuration to be unset. Use dot notation to express hierarchy, e.g., `evp.iot_platform`"
            "For device-specific configurations, use the `--device` option."
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
