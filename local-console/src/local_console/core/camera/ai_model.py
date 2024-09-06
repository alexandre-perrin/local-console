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

import trio
from local_console.clients.agent import Agent
from local_console.core.camera.enums import MQTTTopics
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.state import CameraState
from local_console.core.commands.ota_deploy import configuration_spec
from local_console.core.commands.ota_deploy import get_network_id
from local_console.core.commands.ota_deploy import get_network_ids
from local_console.core.config import config_obj
from local_console.core.schemas.edge_cloud_if_v1 import DnnDelete
from local_console.core.schemas.edge_cloud_if_v1 import DnnDeleteBody
from local_console.core.schemas.schemas import OnWireProtocol
from local_console.servers.webserver import AsyncWebserver
from local_console.utils.local_network import get_webserver_ip

logger = logging.getLogger(__name__)


async def deployment_task(
    camera_state: CameraState, package_file: Path, timeout_notify: Callable
) -> None:
    network_id = get_network_id(package_file)
    logger.debug(f"Undeploying DNN model with ID {network_id}")
    await undeploy_step(camera_state, network_id, timeout_notify)
    logger.debug("Deploying DNN model")
    await deploy_step(camera_state, network_id, package_file, timeout_notify)


async def undeploy_step(
    state: CameraState, network_id: str, timeout_notify: Callable
) -> None:
    config = config_obj.get_config()
    config_device = config_obj.get_active_device_config()
    schema = OnWireProtocol.from_iot_spec(config.evp.iot_platform)
    ephemeral_agent = Agent(config_device.mqtt.host, config_device.mqtt.port, schema)

    timeout_secs = 30
    model_is_deployed = True
    with trio.move_on_after(timeout_secs) as timeout_scope:
        async with ephemeral_agent.mqtt_scope([]):
            await ephemeral_agent.configure(
                "backdoor-EA_Main",
                "placeholder",
                DnnDelete(
                    OTA=DnnDeleteBody(DeleteNetworkID=network_id)
                ).model_dump_json(),
            )
            while True:
                if state.device_config.value:
                    deployed_dnn_model_versions = get_network_ids(
                        state.device_config.value.Version.DnnModelVersion  # type: ignore
                    )
                    logger.debug(
                        f"Deployed DNN model version: {deployed_dnn_model_versions}"
                    )
                    model_is_deployed = network_id in deployed_dnn_model_versions

                    if (
                        state.device_config.value.OTA.UpdateStatus in ["Done", "Failed"]
                        and not model_is_deployed
                    ):
                        logger.debug("DNN model not loaded")
                        break

                await state.ota_event()
                timeout_scope.deadline += timeout_secs

    if model_is_deployed:
        logger.warning("DNN Model hasn't been undeployed")

    if timeout_scope.cancelled_caught:
        timeout_notify()
        logger.error("Timed out attempting to remove previous DNN model")


async def deploy_step(
    state: CameraState,
    network_id: str,
    package_file: Path,
    timeout_notify: Callable,
    use_configured_port: bool = False,
) -> None:
    config = config_obj.get_config()
    config_device = config_obj.get_active_device_config()
    schema = OnWireProtocol.from_iot_spec(config.evp.iot_platform)
    ephemeral_agent = Agent(config_device.mqtt.host, config_device.mqtt.port, schema)
    webserver_port = config_device.webserver.port if use_configured_port else 0

    with TemporaryDirectory(prefix="lc_deploy_") as temporary_dir:
        tmp_dir = Path(temporary_dir)
        tmp_module = tmp_dir / package_file.name
        shutil.copy(package_file, tmp_module)
        ip_addr = get_webserver_ip()

        # In my tests, the "Updating" phase may take this long:
        timeout_secs = 90
        model_is_deployed = False
        with trio.move_on_after(timeout_secs) as timeout_scope:
            async with (
                ephemeral_agent.mqtt_scope(
                    [MQTTTopics.ATTRIBUTES_REQ.value, MQTTTopics.ATTRIBUTES.value]
                ),
                AsyncWebserver(tmp_dir, webserver_port, None, True) as server,
            ):
                assert ephemeral_agent.nursery  # make mypy happy
                # Fill config spec
                spec = configuration_spec(
                    OTAUpdateModule.DNNMODEL, tmp_module, tmp_dir, server.port, ip_addr
                ).model_dump_json()
                logger.debug(f"Update spec is: {spec}")

                await ephemeral_agent.configure("backdoor-EA_Main", "placeholder", spec)
                while True:
                    if state.device_config.value:
                        model_is_deployed = network_id in get_network_ids(
                            state.device_config.value.Version.DnnModelVersion  # type: ignore
                        )

                        if (
                            state.device_config.value.OTA.UpdateStatus
                            in ("Done", "Failed")
                            and model_is_deployed
                        ):
                            break

                    await state.ota_event()
                    timeout_scope.deadline += timeout_secs

        if not model_is_deployed:
            logger.warning("DNN Model is not deployed")

        if timeout_scope.cancelled_caught:
            timeout_notify()
            logger.error("Timed out attempting to deploy DNN model")
