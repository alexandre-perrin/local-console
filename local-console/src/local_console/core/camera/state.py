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
import shutil
from base64 import b64decode
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from typing import Optional

import trio
from local_console.clients.agent import Agent
from local_console.core.camera.axis_mapping import UnitROI
from local_console.core.camera.enums import DeploymentType
from local_console.core.camera.enums import DeployStage
from local_console.core.camera.enums import FirmwareExtension
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.enums import StreamStatus
from local_console.core.camera.flatbuffers import add_class_names
from local_console.core.camera.flatbuffers import flatbuffer_binary_to_json
from local_console.core.camera.flatbuffers import FlatbufferError
from local_console.core.camera.flatbuffers import get_output_from_inference_results
from local_console.core.commands.deploy import deploy_status_empty
from local_console.core.commands.deploy import DeployFSM
from local_console.core.commands.deploy import single_module_manifest_setup
from local_console.core.commands.deploy import verify_report
from local_console.core.commands.ota_deploy import get_package_hash
from local_console.core.config import get_device_persistent_config
from local_console.core.config import update_device_persistent_config
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.schemas import AgentConfiguration
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.gui.drawer.classification import ClassificationDrawer
from local_console.gui.drawer.objectdetection import DetectionDrawer
from local_console.gui.enums import ApplicationConfiguration
from local_console.gui.enums import ApplicationType
from local_console.gui.utils.sync_async import run_on_ui_thread
from local_console.servers.webserver import AsyncWebserver
from local_console.utils.fstools import check_and_create_directory
from local_console.utils.fstools import DirectoryMonitor
from local_console.utils.fstools import StorageSizeWatcher
from local_console.utils.local_network import get_my_ip_by_routing
from local_console.utils.timing import TimeoutBehavior
from local_console.utils.tracking import TrackingVariable
from local_console.utils.validation import validate_imx500_model_file
from pydantic import BaseModel
from pydantic import ValidationError

logger = logging.getLogger(__name__)

MessageType = tuple[str, str]


class CameraStatePersister(BaseModel):
    """
    Class that represents the schema used for persisting the configuration
    from `CameraState`
    """

    module_file: str | None = None
    ai_model_file: str | None = None
    ai_model_file_valid: bool = False


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

    def __init__(
        self,
        message_send_channel: trio.MemorySendChannel[MessageType],
        nursery: trio.Nursery,
        trio_token: trio.lowlevel.TrioToken,
    ) -> None:

        self._nursery: Optional[trio.Nursery] = nursery
        self.trio_token: trio.lowlevel.TrioToken = trio_token
        self._onwire_schema: Optional[OnWireProtocol] = None
        self._last_reception: Optional[datetime] = None

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

        self.module_file: TrackingVariable[Path] = TrackingVariable()
        self.deploy_status: TrackingVariable[dict[str, str]] = TrackingVariable()
        self.deploy_stage: TrackingVariable[DeployStage] = TrackingVariable()
        self.deploy_operation: TrackingVariable[DeploymentType] = TrackingVariable()
        self._deploy_fsm: Optional[DeployFSM] = None

        self.total_dir_watcher = StorageSizeWatcher()
        self.dir_monitor = DirectoryMonitor()

        self.connection_status = TimeoutBehavior(
            CameraState.CONNECTION_STATUS_TIMEOUT.seconds,
            self.connection_status_timeout,
        )
        self.connection_status.spawn_in(self._nursery)

        self.message_send_channel: trio.MemorySendChannel[MessageType] = (
            message_send_channel
        )

        self.stream_image: TrackingVariable[str] = TrackingVariable("")
        self.inference_field: TrackingVariable[str] = TrackingVariable("")
        # Webserver
        self.upload_port: int | None = None
        self.latest_image_file: Optional[Path] = None
        # Used to identify if output tensors are missing
        self.consecutives_images = 0

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

        self.deploy_stage.subscribe_async(self._on_deploy_stage)
        self.deploy_status.subscribe_async(self._on_deploy_status)
        self.deploy_operation.subscribe_async(self._on_deployment_operation)

        def validate_fw_file(current: Optional[Path], previous: Optional[Path]) -> None:
            if current:
                is_valid = True
                if self.firmware_file_type.value == OTAUpdateModule.APFW:
                    if current.suffix != FirmwareExtension.APPLICATION_FW:
                        is_valid = False
                else:
                    if current.suffix != FirmwareExtension.SENSOR_FW:
                        is_valid = False

                self.firmware_file_hash.value = (
                    get_package_hash(current) if is_valid else ""
                )
                self.firmware_file_valid.value = is_valid

        self.firmware_file.subscribe(validate_fw_file)

        self.image_dir_path.subscribe(self.input_directory_setup)
        self.inference_dir_path.subscribe(self.input_directory_setup)

        def validate_ai_model_file(
            current: Optional[Path], previous: Optional[Path]
        ) -> None:
            if current:
                self.ai_model_file_valid.value = validate_imx500_model_file(current)

        self.ai_model_file.subscribe(validate_ai_model_file)

    def input_directory_setup(
        self, current: Optional[Path], previous: Optional[Path]
    ) -> None:
        assert current

        check_and_create_directory(current)
        if previous:
            self.total_dir_watcher.unwatch_path(previous)
        self.total_dir_watcher.set_path(current)

        self.dir_monitor.watch(current, self.notify_directory_deleted)
        if previous:
            self.dir_monitor.unwatch(previous)

    def notify_directory_deleted(self, dir_path: Path) -> None:
        trio.from_thread.run(
            self.message_send_channel.send,
            ("error", str(dir_path) + " does not exist."),
            trio_token=self.trio_token,
        )

    def _create_persister(self) -> CameraStatePersister:
        return CameraStatePersister(
            module_file=str(self.module_file.value),
            ai_model_file=str(self.ai_model_file.value),
            ai_model_file_valid=bool(self.ai_model_file_valid.value),
        )

    def _register_persistency(self, device_name: str) -> None:
        def save_configuration(current: Any, previous: Any) -> None:
            update_device_persistent_config(
                device_name, self._create_persister().model_dump()
            )

        # List of attributes that trigger persistency
        self.module_file.subscribe(save_configuration)
        self.ai_model_file.subscribe(save_configuration)

    def _update_from_persistency(self, device_name: str) -> None:
        # TODO: handle error
        config = CameraStatePersister.model_validate(
            get_device_persistent_config(device_name)
        )
        # Update attributes from persistent configuration
        if config.module_file:
            self.module_file.value = Path(config.module_file)
        if config.ai_model_file:
            self.ai_model_file.value = Path(config.ai_model_file)
            self.ai_model_file_valid.value = config.ai_model_file_valid

    def initialize_persistency(self, device_name: str) -> None:
        self._update_from_persistency(device_name)
        self._register_persistency(device_name)

    async def _on_deploy_status(
        self, current: Optional[dict[str, Any]], previous: Optional[dict[str, Any]]
    ) -> None:
        if self._deploy_fsm is None:
            if deploy_status_empty(current):
                await self.deploy_stage.aset(None)
            else:
                assert current  # See deploy_status_empty(...) above
                is_finished, _, is_errored = verify_report("", current)
                if is_errored:
                    await self.deploy_stage.aset(DeployStage.Error)
                else:
                    if is_finished:
                        await self.deploy_stage.aset(DeployStage.Done)
                    else:
                        await self.deploy_stage.aset(DeployStage.WaitFirstStatus)
        else:
            if current:
                await self._deploy_fsm.update(current)

    async def _on_deployment_operation(
        self, current: Optional[DeploymentType], previous: Optional[DeploymentType]
    ) -> None:
        if previous != current:
            if current == DeploymentType.Application:
                assert self._deploy_fsm
                assert self._nursery
                await self._deploy_fsm.start(self._nursery)
            elif not current:
                self._deploy_fsm = None

    async def _on_deploy_stage(
        self, current: Optional[DeployStage], previous: Optional[DeployStage]
    ) -> None:
        if current in (DeployStage.Done, DeployStage.Error):
            await self.deploy_operation.aset(None)

    async def do_app_deployment(self, agent: Agent) -> None:
        assert self.module_file.value
        assert self._deploy_fsm is None

        self._deploy_fsm = DeployFSM.instantiate(
            agent.onwire_schema, agent.deploy, self.deploy_stage.aset
        )
        manifest = single_module_manifest_setup(
            ApplicationConfiguration.NAME,
            self.module_file.value,
            self._deploy_fsm.webserver,
        )
        self._deploy_fsm.set_manifest(manifest)
        await self.deploy_operation.aset(DeploymentType.Application)

    async def connection_status_timeout(self) -> None:
        logger.debug("Connection status timed out: camera is disconnected")
        self.stream_status.value = StreamStatus.Inactive
        self._check_connection_status()

    def initialize_connection_variables(self, config: AgentConfiguration) -> None:
        self.local_ip.value = get_my_ip_by_routing()
        self.mqtt_host.value = config.mqtt.host.ip_value
        self.mqtt_port.value = str(config.mqtt.port)
        self.ntp_host.value = "pool.ntp.org"

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

        self.connection_status.tap()

    async def _process_state_topic(self, payload: dict[str, Any]) -> None:
        firmware_is_supported = False
        try:
            decoded = json.loads(b64decode(payload[self.EA_STATE_TOPIC]))
            firmware_is_supported = True
        except UnicodeDecodeError:
            decoded = json.loads(payload[self.EA_STATE_TOPIC])

        if firmware_is_supported:
            try:
                await self.device_config.aset(
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
            update = json.loads(payload[self.DEPLOY_STATUS_TOPIC])
        else:
            update = payload[self.DEPLOY_STATUS_TOPIC]

        self.attributes_available.value = True
        await self.deploy_status.aset(update)

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

    def _save_into_input_directory(self, incoming_file: Path, target_dir: Path) -> Path:
        assert incoming_file.is_file()

        """
        The following cannot be asserted in the current implementation
        based on temporary directories, because of unexpected OS deletion
        of the target directory if it hasn't been set to the default
        temporary directory.
        """
        # assert target_dir.is_dir()

        final = incoming_file
        check_and_create_directory(final.parent)
        if incoming_file.parent != target_dir:
            check_and_create_directory(target_dir)
            final = Path(shutil.move(incoming_file, target_dir))
        self.total_dir_watcher.incoming(final)
        return final

    def _get_flatbuffers_inference_data(
        self, flatbuffer_payload: bytes
    ) -> None | str | dict:
        return_value = None
        if self.vapp_schema_file.value:
            json_data = flatbuffer_binary_to_json(
                self.vapp_schema_file.value, flatbuffer_payload
            )
            labels_map = self.vapp_labels_map.value
            if labels_map:
                add_class_names(json_data, labels_map)
            return_value = json_data

        return return_value

    def _process_camera_upload(self, incoming_file: Path) -> None:
        if incoming_file.parent.name == "inferences":
            target_dir = self.inference_dir_path.value
            assert target_dir
            final_file = self._save_into_input_directory(incoming_file, target_dir)
            output_data = get_output_from_inference_results(final_file.read_bytes())

            payload_render = final_file.read_text()
            if self.vapp_schema_file.value:
                try:
                    output_tensor = self._get_flatbuffers_inference_data(output_data)
                    if output_tensor:
                        payload_render = json.dumps(output_tensor, indent=2)
                        output_data = output_tensor  # type: ignore
                except FlatbufferError as e:
                    logger.error("Error decoding inference data:", exc_info=e)

            self.inference_field.value = payload_render
            # assumes input and output tensor received in that order
            assert self.latest_image_file
            try:
                {
                    ApplicationType.CLASSIFICATION.value: ClassificationDrawer,
                    ApplicationType.DETECTION.value: DetectionDrawer,
                }[str(self.vapp_type.value)].process_frame(
                    self.latest_image_file, output_data
                )
            except Exception as e:
                logger.error(f"Error while performing the drawing: {e}")
            self.stream_image.value = str(self.latest_image_file)
            self.consecutives_images = 0

        elif incoming_file.parent.name == "images":
            assert self.image_dir_path.value
            final_file = self._save_into_input_directory(
                incoming_file, self.image_dir_path.value
            )
            self.latest_image_file = final_file
            if self.consecutives_images > 0:
                self.stream_image.value = str(self.latest_image_file)
            self.consecutives_images += 1
        else:
            logger.warning(f"Unknown incoming file: {incoming_file}")

    @run_on_ui_thread
    def __process_camera_upload(self, incoming_file: Path) -> None:
        self._process_camera_upload(incoming_file)

    async def blobs_webserver_task(self) -> None:
        """
        Spawn a webserver on an arbitrary available port for receiving
        images from a camera.
        :param on_received: Callback that is triggered for each new received image
        :param base_dir: Path to directory where images will be saved into
        :return:
        """
        with (
            TemporaryDirectory(prefix="LocalConsole_") as tempdir,
            AsyncWebserver(
                Path(tempdir), port=0, on_incoming=self.__process_camera_upload
            ) as image_serve,
        ):
            logger.info(f"Uploading data into {tempdir}")

            assert image_serve.port
            self.upload_port = image_serve.port
            logger.info(f"Webserver listening on port {self.upload_port}")
            tmp_image_directory = Path(tempdir) / "images"
            tmp_inference_directory = Path(tempdir) / "inferences"
            tmp_image_directory.mkdir(exist_ok=True)
            tmp_inference_directory.mkdir(exist_ok=True)

            self.image_dir_path.value = tmp_image_directory
            self.inference_dir_path.value = tmp_inference_directory

            await trio.sleep_forever()
