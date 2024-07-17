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
from base64 import b64decode
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any
from typing import Optional

import trio
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.enums import StreamStatus
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.utils.tracking import TrackingVariable
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class CameraState:
    """
    This class holds all information that represents the state
    of a camera, which is comprised of:
    - Status reports from the camera firmware.
    - User settings that parametrize the camera functions.
    """

    EA_STATE_TOPIC = "state/backdoor-EA_Main/placeholder"
    SYSINFO_TOPIC = "systemInfo"
    DEPLOY_STATUS_TOPIC = "deploymentStatus"

    CONNECTION_STATUS_TIMEOUT = timedelta(seconds=180)

    def __init__(self) -> None:
        self.sensor_state = StreamStatus.Inactive
        self.deploy_status: dict[str, str] = {}
        self._onwire_schema: Optional[OnWireProtocol] = None
        self.device_config: TrackingVariable[DeviceConfiguration] = TrackingVariable()
        self.attributes_available = False
        self._last_reception: Optional[datetime] = None

        self._ota_event = trio.Event()
        self.device_config.subscribe_async(self._prepare_ota_event)

        self.ai_model_file: TrackingVariable[Path] = TrackingVariable()
        self.ai_model_file_valid: TrackingVariable[bool] = TrackingVariable(False)

        self.firmware_file: TrackingVariable[Path] = TrackingVariable()
        self.firmware_file_valid: TrackingVariable[bool] = TrackingVariable(False)
        self.firmware_file_version: TrackingVariable[str] = TrackingVariable()
        self.firmware_file_type: TrackingVariable[OTAUpdateModule] = TrackingVariable()
        self.firmware_file_hash: TrackingVariable[str] = TrackingVariable()

        self.image_dir_path: TrackingVariable[Path] = TrackingVariable()
        self.inference_dir_path: TrackingVariable[Path] = TrackingVariable()

    @property
    def is_ready(self) -> bool:
        # Attributes report interval cannot be controlled in EVP1
        return (
            self.onwire_schema is not OnWireProtocol.EVP1 and self.attributes_available
        )

    @property
    def connected(self) -> bool:
        if self._last_reception is None:
            return False
        else:
            return (
                datetime.now() - self._last_reception
            ) < self.CONNECTION_STATUS_TIMEOUT

    @property
    def is_streaming(self) -> bool:
        return self.sensor_state == StreamStatus.Active

    async def process_incoming(self, topic: str, payload: dict[str, Any]) -> None:
        sent_from_camera = False
        if topic == MQTTTopics.ATTRIBUTES.value:
            if self.EA_STATE_TOPIC in payload:
                sent_from_camera = True
                await self._process_state_topic(payload)

            if self.SYSINFO_TOPIC in payload:
                sent_from_camera = True
                await self._process_sysinfo_topic(payload)

            if self.DEPLOY_STATUS_TOPIC in payload:
                sent_from_camera = True
                await self._process_deploy_status_topic(payload)

        if topic == MQTTTopics.TELEMETRY.value:
            sent_from_camera = True

        if sent_from_camera:
            self._last_reception = datetime.now()
            logger.debug("Incoming on %s: %s", topic, str(payload))

    async def _process_state_topic(self, payload: dict[str, Any]) -> None:
        firmware_is_supported = False
        try:
            decoded = json.loads(b64decode(payload[self.EA_STATE_TOPIC]))
            firmware_is_supported = True
        except UnicodeDecodeError:
            decoded = json.loads(payload[self.EA_STATE_TOPIC])

        if firmware_is_supported:
            try:
                await self.device_config.set(
                    DeviceConfiguration.model_validate(decoded)
                )
                if self.device_config.value:
                    self.sensor_state = StreamStatus.from_string(
                        self.device_config.value.Status.Sensor
                    )
            except ValidationError as e:
                logger.warning(f"Error while validating device configuration: {e}")

    async def _process_sysinfo_topic(self, payload: dict[str, Any]) -> None:
        sys_info = payload[self.SYSINFO_TOPIC]
        if "protocolVersion" in sys_info:
            self.onwire_schema = OnWireProtocol(sys_info["protocolVersion"])
        self.attributes_available = True

    async def _process_deploy_status_topic(self, payload: dict[str, Any]) -> None:
        if self.onwire_schema == OnWireProtocol.EVP1 or self.onwire_schema is None:
            self.deploy_status = json.loads(payload[self.DEPLOY_STATUS_TOPIC])
        else:
            self.deploy_status = payload[self.DEPLOY_STATUS_TOPIC]
        self.attributes_available = True

    async def _prepare_ota_event(
        self,
        current: Optional[DeviceConfiguration],
        previous: Optional[DeviceConfiguration],
    ) -> None:
        if current != previous:
            self._ota_event.set()

    async def ota_event(self) -> None:
        self._ota_event = trio.Event()
        await self._ota_event.wait()
