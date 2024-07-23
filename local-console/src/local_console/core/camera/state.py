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
from local_console.core.camera.axis_mapping import UnitROI
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.enums import StreamStatus
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.schemas import AgentConfiguration
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.utils.local_network import get_my_ip_by_routing
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

    # For Connection view
    MAX_LEN_DOMAIN_NAME = int(64)
    MAX_LEN_IP_ADDRESS = int(39)
    MAX_LEN_PORT = int(5)
    MAX_LEN_WIFI_SSID = int(32)
    MAX_LEN_WIFI_PASSWORD = int(32)

    def __init__(self) -> None:

        self._onwire_schema: Optional[OnWireProtocol] = None
        self._last_reception: Optional[datetime] = None

        self.deploy_status: TrackingVariable[dict[str, str]] = TrackingVariable()
        self.device_config: TrackingVariable[DeviceConfiguration] = TrackingVariable()
        self.attributes_available: TrackingVariable[bool] = TrackingVariable(False)
        self.is_connected: TrackingVariable[bool] = TrackingVariable(False)
        self.is_ready: TrackingVariable[bool] = TrackingVariable(False)
        self.stream_status: TrackingVariable[StreamStatus] = TrackingVariable(
            StreamStatus.Inactive
        )
        self.is_streaming: TrackingVariable[bool] = TrackingVariable(False)
        self.roi: TrackingVariable[UnitROI] = TrackingVariable()

        self._ota_event = trio.Event()
        self.device_config.subscribe_async(self._prepare_ota_event)

        self.ai_model_file: TrackingVariable[Path] = TrackingVariable()
        self.ai_model_file_valid: TrackingVariable[bool] = TrackingVariable(False)
        self.vapp_schema_file: TrackingVariable[Path] = TrackingVariable()
        self.vapp_config_file: TrackingVariable[Path] = TrackingVariable()
        self.vapp_labels_file: TrackingVariable[Path] = TrackingVariable()
        self.vapp_type: TrackingVariable[str] = TrackingVariable()
        self.vapp_labels_map: TrackingVariable[dict[int, str]] = TrackingVariable()

        self.firmware_file: TrackingVariable[Path] = TrackingVariable()
        self.firmware_file_valid: TrackingVariable[bool] = TrackingVariable(False)
        self.firmware_file_version: TrackingVariable[str] = TrackingVariable()
        self.firmware_file_type: TrackingVariable[OTAUpdateModule] = TrackingVariable()
        self.firmware_file_hash: TrackingVariable[str] = TrackingVariable()

        self.image_dir_path: TrackingVariable[Path] = TrackingVariable()
        self.inference_dir_path: TrackingVariable[Path] = TrackingVariable()

        self.local_ip: TrackingVariable[str] = TrackingVariable("")
        self.mqtt_host: TrackingVariable[str] = TrackingVariable("")
        self.mqtt_port: TrackingVariable[str] = TrackingVariable("")
        self.ntp_host: TrackingVariable[str] = TrackingVariable("")
        self.ip_address: TrackingVariable[str] = TrackingVariable("")
        self.subnet_mask: TrackingVariable[str] = TrackingVariable("")
        self.gateway: TrackingVariable[str] = TrackingVariable("")
        self.dns_server: TrackingVariable[str] = TrackingVariable("")
        self.wifi_ssid: TrackingVariable[str] = TrackingVariable("")
        self.wifi_password: TrackingVariable[str] = TrackingVariable("")
        self.wifi_password_hidden: TrackingVariable[bool] = TrackingVariable(True)
        self.wifi_icon_eye: TrackingVariable[str] = TrackingVariable("")

        self._init_bindings()

    def _init_bindings(self) -> None:
        """
        These bindings among variables implement business logic that requires
        no further data than the one contained among the variables.
        """

        def compute_is_ready(current: Optional[bool], previous: Optional[bool]) -> None:
            _is_ready = (
                False
                if current is None
                else (
                    # Attributes report interval cannot be controlled in EVP1
                    current
                    and (self._onwire_schema is not OnWireProtocol.EVP1)
                )
            )
            self.is_ready.value = _is_ready

        self.attributes_available.subscribe(compute_is_ready)

        def compute_is_streaming(
            current: Optional[StreamStatus], previous: Optional[StreamStatus]
        ) -> None:
            _is_streaming = (
                False if current is None else (current == StreamStatus.Active)
            )
            self.is_streaming.value = _is_streaming

        self.stream_status.subscribe(compute_is_streaming)

    def initialize_connection_variables(self, config: AgentConfiguration) -> None:
        self.local_ip.value = get_my_ip_by_routing()
        self.mqtt_host.value = config.mqtt.host.ip_value
        self.mqtt_port.value = str(config.mqtt.port)
        self.ntp_host.value = "pool.ntp.org"
        self.wifi_icon_eye.value = "eye-off"

    def _check_connection_status(self) -> bool:
        if self._last_reception is None:
            return False
        else:
            return (
                datetime.now() - self._last_reception
            ) < self.CONNECTION_STATUS_TIMEOUT

    def update_connection_status(self) -> None:
        self.is_connected.value = self._check_connection_status()

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
                    self.stream_status.value = StreamStatus.from_string(
                        self.device_config.value.Status.Sensor
                    )
            except ValidationError as e:
                logger.warning(f"Error while validating device configuration: {e}")

    async def _process_sysinfo_topic(self, payload: dict[str, Any]) -> None:
        sys_info = payload[self.SYSINFO_TOPIC]
        if "protocolVersion" in sys_info:
            self._onwire_schema = OnWireProtocol(sys_info["protocolVersion"])
        self.attributes_available.value = True

    async def _process_deploy_status_topic(self, payload: dict[str, Any]) -> None:
        if self._onwire_schema == OnWireProtocol.EVP1 or self._onwire_schema is None:
            self.deploy_status.value = json.loads(payload[self.DEPLOY_STATUS_TOPIC])
        else:
            self.deploy_status.value = payload[self.DEPLOY_STATUS_TOPIC]
        self.attributes_available.value = True

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
