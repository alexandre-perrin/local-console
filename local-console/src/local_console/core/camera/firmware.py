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
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable
from typing import Optional

import trio
from local_console.clients.agent import Agent
from local_console.core.camera.enums import FirmwareExtension
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.enums import OTAUpdateStatus
from local_console.core.camera.state import CameraState
from local_console.core.commands.ota_deploy import configuration_spec
from local_console.core.config import config_obj
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.servers.webserver import AsyncWebserver
from local_console.utils.local_network import get_webserver_ip

logger = logging.getLogger(__name__)


class FirmwareException(Exception):
    """
    Used for conveying error messages in a framework-agnostic way
    """


class TransientStatus:
    """
    A simple holder of values that is updated dynamically during
    a firmware update operation. This present form can be used
    for unit tests, and in the GUI it is subclassed by a type that
    provides automatic event chaining for displaying the current
    status on the screen for the user to get feedback.
    """

    update_status: str = ""
    progress_download: int = 0
    progress_update: int = 0


def validate_firmware_file(
    file_path: Path,
    file_type: OTAUpdateModule,
    version: str,
    current_cfg: Optional[DeviceConfiguration],
) -> bool:

    if not file_path.is_file():
        raise FirmwareException("Firmware file does not exist!")

    if current_cfg is None:
        logger.debug("DeviceConfiguration is None.")
        return False

    if file_type == OTAUpdateModule.APFW:
        if file_path.suffix != FirmwareExtension.APPLICATION_FW:
            raise FirmwareException("Invalid Application Firmware!")

        if current_cfg.Version.ApFwVersion == version:
            raise FirmwareException("Version is the same as the current firmware.")
    else:
        if file_path.suffix != FirmwareExtension.SENSOR_FW:
            raise FirmwareException("Invalid Sensor Firmware!")

        if current_cfg.Version.SensorFwVersion == version:
            raise FirmwareException("Version is the same as the current firmware.")

    return True


def progress_update_checkpoint(
    device_config: DeviceConfiguration, indicator: type[TransientStatus]
) -> bool:
    done = False

    update_status = device_config.OTA.UpdateStatus
    update_progress = device_config.OTA.UpdateProgress

    if update_status == OTAUpdateStatus.DOWNLOADING:
        indicator.progress_download = update_progress
        indicator.progress_update = 0

    elif update_status == OTAUpdateStatus.UPDATING:
        indicator.progress_download = 100
        indicator.progress_update = update_progress

    elif update_status == OTAUpdateStatus.REBOOTING:
        indicator.progress_download = 100
        indicator.progress_update = 100

    elif update_status == OTAUpdateStatus.DONE:
        indicator.progress_download = 100
        indicator.progress_update = 100
        done = True

    elif update_status == OTAUpdateStatus.FAILED:
        done = True

    indicator.update_status = update_status
    return done


async def update_firmware_task(
    state: CameraState,
    indicator: type[TransientStatus],
    error_notify: Callable,
    use_configured_port: bool = False,
) -> None:
    assert state.firmware_file.value
    assert state.firmware_file_type.value
    assert state.firmware_file_version.value

    indicator.progress_download = 0
    indicator.progress_update = 0
    indicator.update_status = ""

    valid = False
    try:
        valid = validate_firmware_file(
            state.firmware_file.value,
            state.firmware_file_type.value,
            state.firmware_file_version.value,
            state.device_config.value,
        )
    except FirmwareException as e:
        error_notify(str(e))
    if not valid:
        return

    config = config_obj.get_config()
    config_device = config_obj.get_active_device_config()
    schema = OnWireProtocol.from_iot_spec(config.evp.iot_platform)
    ephemeral_agent = Agent(config_device.mqtt.host, config_device.mqtt.port, schema)
    webserver_port = config_device.webserver.port if use_configured_port else 0
    ip_addr = get_webserver_ip()

    with TemporaryDirectory(prefix="lc_update_") as temporary_dir:
        tmp_dir = Path(temporary_dir)
        tmp_firmware = tmp_dir / state.firmware_file.value.name
        shutil.copy(state.firmware_file.value, tmp_firmware)

        logger.debug("Firmware update operation will start.")
        timeout_secs = 60 * 4
        with trio.move_on_after(timeout_secs) as timeout_scope:
            async with (
                ephemeral_agent.mqtt_scope(
                    [MQTTTopics.ATTRIBUTES_REQ.value, MQTTTopics.ATTRIBUTES.value]
                ),
                AsyncWebserver(tmp_dir, webserver_port, None, True) as serve,
            ):
                # Fill config spec
                update_spec = configuration_spec(
                    state.firmware_file_type.value,
                    tmp_firmware,
                    tmp_dir,
                    serve.port,
                    ip_addr,
                )
                # Use version specified by the user
                update_spec.OTA.DesiredVersion = state.firmware_file_version.value

                payload = update_spec.model_dump_json()
                logger.debug(f"Update spec is: {payload}")

                await ephemeral_agent.configure(
                    "backdoor-EA_Main", "placeholder", payload
                )
                while True:
                    """
                    This loop assumes that `state` is updated by a main
                    loop that reacts to reports from the camera, such as
                    `Driver.mqtt_setup`.
                    """
                    await state.ota_event()
                    timeout_scope.deadline += timeout_secs

                    if state.device_config.value:
                        if progress_update_checkpoint(
                            state.device_config.value, indicator
                        ):
                            logger.debug("Finished updating.")
                            break

        if timeout_scope.cancelled_caught:
            error_notify("Firmware update timed out!")
            logger.warning("Timeout while updating firmware.")

        logger.debug("Firmware update operation is finished.")
