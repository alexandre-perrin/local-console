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
from pathlib import Path
from typing import Any
from typing import Optional

import trio
from local_console.core.camera._shared import MessageType
from local_console.core.camera.enums import DeploymentType
from local_console.core.camera.enums import DeployStage
from local_console.core.camera.enums import FirmwareExtension
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.mixin_mqtt import MQTTMixin
from local_console.core.camera.mixin_streaming import StreamingMixin
from local_console.core.commands.deploy import deploy_status_empty
from local_console.core.commands.deploy import DeployFSM
from local_console.core.commands.deploy import single_module_manifest_setup
from local_console.core.commands.deploy import verify_report
from local_console.core.commands.ota_deploy import get_package_hash
from local_console.gui.enums import ApplicationConfiguration
from local_console.utils.tracking import TrackingVariable
from local_console.utils.validation import validate_imx500_model_file
from trio import CancelScope
from trio import MemorySendChannel
from trio import Nursery
from trio import TASK_STATUS_IGNORED
from trio.lowlevel import TrioToken

logger = logging.getLogger(__name__)


class CameraState(MQTTMixin, StreamingMixin):
    """
    This class holds all information that represents the state
    of a camera, which is comprised of:
    - Status reports from the camera firmware.
    - User settings that parametrize the camera functions.
    """

    # For Connection view
    MAX_LEN_DOMAIN_NAME = int(64)
    MAX_LEN_IP_ADDRESS = int(39)
    MAX_LEN_PORT = int(5)
    MAX_LEN_WIFI_SSID = int(32)
    MAX_LEN_WIFI_PASSWORD = int(32)

    def __init__(
        self,
        message_send_channel: MemorySendChannel[MessageType],
        trio_token: TrioToken,
    ) -> None:
        MQTTMixin.__init__(self)
        StreamingMixin.__init__(self)

        self.message_send_channel = message_send_channel
        self.trio_token: TrioToken = trio_token
        self._nursery: Optional[Nursery] = None
        self._cancel_scope: Optional[CancelScope] = None
        self._started = trio.Event()
        self._stopped = trio.Event()

        # State variables not provided by mixin classes
        self.ai_model_file: TrackingVariable[str] = TrackingVariable()
        self.ai_model_file_valid: TrackingVariable[bool] = TrackingVariable(False)

        self.firmware_file: TrackingVariable[Path] = TrackingVariable()
        self.firmware_file_valid: TrackingVariable[bool] = TrackingVariable(False)
        self.firmware_file_version: TrackingVariable[str] = TrackingVariable()
        self.firmware_file_type: TrackingVariable[OTAUpdateModule] = TrackingVariable()
        self.firmware_file_hash: TrackingVariable[str] = TrackingVariable()

        self.module_file: TrackingVariable[Path] = TrackingVariable()
        self.deploy_status: TrackingVariable[dict[str, str]] = TrackingVariable()
        self.deploy_stage: TrackingVariable[DeployStage] = TrackingVariable()
        self.deploy_operation: TrackingVariable[DeploymentType] = TrackingVariable()
        self._deploy_fsm: Optional[DeployFSM] = None

        self._init_bindings()

    def _init_bindings(self) -> None:
        """
        These bindings among variables implement business logic that requires
        no further data than the one contained among the variables.
        """
        self._init_bindings_mqtt()
        self._init_bindings_streaming()

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

        def validate_ai_model_file(
            current: Optional[str], previous: Optional[str]
        ) -> None:
            if current:
                self.ai_model_file_valid.value = validate_imx500_model_file(
                    Path(current)
                )

        self.ai_model_file.subscribe(validate_ai_model_file)

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

    async def do_app_deployment(self) -> None:
        assert self.mqtt_client
        assert self.module_file.value
        assert self._deploy_fsm is None

        self._deploy_fsm = DeployFSM.instantiate(
            self.mqtt_client.onwire_schema,
            self.mqtt_client.deploy,
            self.deploy_stage.aset,
        )
        manifest = single_module_manifest_setup(
            ApplicationConfiguration.NAME,
            self.module_file.value,
            self._deploy_fsm.webserver,
        )
        self._deploy_fsm.set_manifest(manifest)
        await self.deploy_operation.aset(DeploymentType.Application)

    async def startup(self, *, task_status: Any = TASK_STATUS_IGNORED) -> None:
        async with trio.open_nursery() as nursery:
            if not await nursery.start(self.mqtt_setup):
                task_status.started(False)
                return

            nursery.start_soon(self.blobs_webserver_task)
            self.dir_monitor.start()

            self._nursery = nursery
            self._cancel_scope = nursery.cancel_scope
            self._started.set()
            task_status.started(True)

        self._stopped.set()
        logger.debug(f"Device on port {self.mqtt_port.value} shut down")

    def shutdown(self) -> None:
        if self._started.is_set():
            assert self._cancel_scope
            self.dir_monitor.stop()
            self._cancel_scope.cancel()

    async def send_app_config(self, config: str) -> None:
        assert self.mqtt_client
        await self.mqtt_client.configure(
            ApplicationConfiguration.NAME,
            ApplicationConfiguration.CONFIG_TOPIC,
            config,
        )

    async def streaming_rpc_stop(self) -> None:
        """
        Unfortunately the inheritance mechanism forces us to have
        this explicit instantiation, so that static typing checks
        succeed.
        """
        await StreamingMixin.streaming_rpc_stop(self)
