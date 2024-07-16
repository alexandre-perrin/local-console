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
from pathlib import PurePath
from tempfile import TemporaryDirectory

import trio
from local_console.clients.agent import Agent
from local_console.core.camera import MQTTTopics
from local_console.core.commands.ota_deploy import configuration_spec
from local_console.core.commands.ota_deploy import get_package_hash
from local_console.core.config import get_config
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.gui.driver import Driver
from local_console.gui.model.firmware_screen import FirmwareScreenModel
from local_console.gui.view.firmware_screen.firmware_screen import FirmwareScreenView
from local_console.servers.webserver import AsyncWebserver
from local_console.utils.local_network import get_my_ip_by_routing

logger = logging.getLogger(__name__)


class FirmwareScreenController:
    """
    The `FirmwareScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.

    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model: FirmwareScreenModel, driver: Driver):
        self.model = model
        self.driver = driver
        self.view = FirmwareScreenView(controller=self, model=self.model)

    def get_view(self) -> FirmwareScreenView:
        return self.view

    def select_path(self, path_str: str) -> None:
        """
        Called when an uesr clicks on the file name.

        :param path_str: path to the selected file;
        """
        firmware_path = Path(path_str)
        self.model.firmware_file = firmware_path

        if self.model.firmware_file_type == OTAUpdateModule.APFW:
            if firmware_path.suffix != FirmwareExtension.APPLICATION_FW:
                self.model.firmware_file_valid = False
                self.view.display_error("Invalid Application Firmware!")
                return
        else:
            if firmware_path.suffix != FirmwareExtension.SENSOR_FW:
                self.model.firmware_file_valid = False
                self.view.display_error("Invalid Sensor Firmware!")
                return

        self.model.firmware_file_hash = get_package_hash(firmware_path)
        self.model.firmware_file_valid = True

    def select_firmware_type(self, type: str) -> None:
        """
        Called when an user selects the firmware type.
        """
        if type == FirmwareType.APPLICATION_FW:
            self.model.firmware_file_type = OTAUpdateModule.APFW
        else:
            self.model.firmware_file_type = OTAUpdateModule.SENSORFW

    def set_firmware_version(self, text: str) -> None:
        """
        Called when an user inputs the firmware version.
        """
        self.model.firmware_file_version = text

    def update_firmware(self) -> None:
        """
        Called when an user clicks the update button.
        """
        if not self.view.ids.btn_update_firmware.disabled:
            self.view.ids.btn_update_firmware.disabled = True
            self.driver.from_sync(self.update_firmware_task, self.model.firmware_file)
        else:
            logger.warning("The firmware update button is disabled")

    def validate_firmware_file(self, firmware_file: Path) -> bool:
        if not isinstance(firmware_file, PurePath) or not firmware_file.resolve():
            self.view.display_error("Firmware file does not exist!")
            return False

        if self.model.device_config is None:
            logger.debug("DeviceConfiguration is None.")
            return False

        if self.model.firmware_file_type == OTAUpdateModule.APFW:
            if firmware_file.suffix != FirmwareExtension.APPLICATION_FW:
                self.view.display_error("Invalid Application Firmware!")
                return False

            if (
                self.model.device_config.Version.ApFwVersion
                == self.model.firmware_file_version
            ):
                self.view.display_error("Version is the same as the current firmware.")
                return False
        else:
            if firmware_file.suffix != FirmwareExtension.SENSOR_FW:
                self.view.display_error("Invalid Sensor Firmware!")
                return False

            if (
                self.model.device_config.Version.SensorFwVersion
                == self.model.firmware_file_version
            ):
                self.view.display_error("Version is the same as the current firmware.")
                return False

        return True

    def update_progress_bar(self, dev_config_prev: DeviceConfiguration | None) -> bool:
        if self.model.device_config and self.model.device_config != dev_config_prev:
            update_status = self.model.device_config.OTA.UpdateStatus
            update_progress = self.model.device_config.OTA.UpdateProgress
            self.model.update_status = update_status
            if update_status == OTAUpdateStatus.DOWNLOADING:
                self.model.downloading_progress = update_progress
                self.model.updating_progress = 0
            elif update_status == OTAUpdateStatus.UPDATING:
                self.model.downloading_progress = 100
                self.model.updating_progress = update_progress
            elif update_status == OTAUpdateStatus.REBOOTING:
                self.model.downloading_progress = 100
                self.model.updating_progress = 100
            elif update_status == OTAUpdateStatus.DONE:
                self.model.downloading_progress = 100
                self.model.updating_progress = 100
                return True
            elif update_status == OTAUpdateStatus.FAILED:
                return True
        return False

    async def update_firmware_task(self, firmware_file: Path) -> None:
        self.model.downloading_progress = 0
        self.model.updating_progress = 0
        self.model.update_status = ""

        if not self.validate_firmware_file(firmware_file):
            logger.warning("Firmware file is not valid.")
            return

        config = get_config()
        ephemeral_agent = Agent()
        webserver_port = config.webserver.port

        with TemporaryDirectory(prefix="lc_update_") as temporary_dir:
            tmp_dir = Path(temporary_dir)
            tmp_firmware = tmp_dir / firmware_file.name
            shutil.copy(firmware_file, tmp_firmware)
            ip_addr = get_my_ip_by_routing()

            update_spec = configuration_spec(
                tmp_firmware, tmp_dir, webserver_port, ip_addr
            )
            update_spec.OTA.UpdateModule = self.model.firmware_file_type
            update_spec.OTA.DesiredVersion = self.model.firmware_file_version

            timeout_secs = 60 * 4
            with trio.move_on_after(timeout_secs) as timeout_scope:
                async with (
                    ephemeral_agent.mqtt_scope(
                        [MQTTTopics.ATTRIBUTES_REQ.value, MQTTTopics.ATTRIBUTES.value]
                    ),
                    AsyncWebserver(tmp_dir, webserver_port, None, True),
                ):
                    device_config_previous = self.model.device_config
                    assert ephemeral_agent.nursery  # make mypy happy
                    await ephemeral_agent.configure(
                        "backdoor-EA_Main", "placeholder", update_spec.model_dump_json()
                    )
                    logger.debug(update_spec.model_dump_json())
                    while True:
                        if self.update_progress_bar(device_config_previous):
                            logger.debug("Finished updating.")
                            break
                        device_config_previous = self.model.device_config
                        await self.model.ota_event()
                        timeout_scope.deadline += timeout_secs

            if timeout_scope.cancelled_caught:
                self.view.display_error("Firmware update timed out!")
                logger.warning("Timeout while updating firmware.")
