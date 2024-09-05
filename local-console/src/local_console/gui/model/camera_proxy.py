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
from pathlib import Path

from kivy.properties import BooleanProperty
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
from local_console.core.camera.axis_mapping import DEFAULT_ROI
from local_console.core.camera.enums import DeploymentType
from local_console.core.camera.enums import DeployStage
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.enums import StreamStatus
from local_console.core.camera.state import CameraState
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.gui.enums import ApplicationType
from local_console.gui.model.data_binding import CameraStateProxyBase


class CameraStateProxy(CameraStateProxyBase):

    is_connected = BooleanProperty(False)
    is_ready = BooleanProperty(False)
    is_streaming = BooleanProperty(False)
    stream_status = ObjectProperty(StreamStatus.Inactive)
    roi = ObjectProperty(DEFAULT_ROI)

    image_dir_path = StringProperty("")
    inference_dir_path = StringProperty("")

    device_config = ObjectProperty(DeviceConfiguration, allownone=True)

    ai_model_file = StringProperty("", allownone=True)

    # About force_dispatch, please check docstring of
    # test_camera_proxy.py::test_difference_of_property_with_force_dispatch
    ai_model_file_valid = BooleanProperty(False, force_dispatch=True)

    vapp_schema_file = ObjectProperty("")
    vapp_config_file = ObjectProperty("")
    vapp_labels_file = ObjectProperty("")
    vapp_labels_map = ObjectProperty({}, allownone=True)
    vapp_type = StringProperty(ApplicationType.CUSTOM.value)

    firmware_file = StringProperty("", allownone=True)
    firmware_file_valid = BooleanProperty(False, force_dispatch=True)
    firmware_file_version = StringProperty("", allownone=True)
    firmware_file_type = ObjectProperty(OTAUpdateModule, allownone=True)
    firmware_file_hash = StringProperty("", allownone=True)

    mqtt_host = StringProperty("")
    mqtt_port = StringProperty("")
    ntp_host = StringProperty("")
    ip_address = StringProperty("")
    subnet_mask = StringProperty("")
    gateway = StringProperty("")
    dns_server = StringProperty("")
    wifi_ssid = StringProperty("")
    wifi_password = StringProperty("")

    module_file = StringProperty("", allownone=True)
    deploy_status = StringProperty("", allownone=True)
    deploy_stage = ObjectProperty(DeployStage, allownone=True)
    deploy_operation = ObjectProperty(DeploymentType, allownone=True)

    stream_image = StringProperty("")
    inference_field = StringProperty("")

    size = StringProperty("100")
    unit = StringProperty("MB")

    def bind_connections(self, camera_state: CameraState) -> None:
        self.bind_state_to_proxy("mqtt_host", camera_state)
        self.bind_state_to_proxy("mqtt_port", camera_state, str)
        self.bind_state_to_proxy("ntp_host", camera_state)
        self.bind_state_to_proxy("ip_address", camera_state)
        self.bind_state_to_proxy("subnet_mask", camera_state)
        self.bind_state_to_proxy("gateway", camera_state)
        self.bind_state_to_proxy("dns_server", camera_state)
        self.bind_state_to_proxy("wifi_ssid", camera_state)
        self.bind_state_to_proxy("wifi_password", camera_state)

        # to propagate initialization in `CameraState`
        self.bind_state_to_proxy("is_connected", camera_state)

    def bind_core_variables(self, camera_state: CameraState) -> None:
        self.bind_state_to_proxy("is_ready", camera_state)
        self.bind_state_to_proxy("is_streaming", camera_state)
        self.bind_state_to_proxy("device_config", camera_state)
        self.bind_proxy_to_state("unit", camera_state)
        self.bind_proxy_to_state("size", camera_state)

    def bind_stream_variables(self, camera_state: CameraState) -> None:
        # Proxy->State because we want the user to set this value via the GUI
        self.bind_proxy_to_state("roi", camera_state)

        # State->Proxy because this is either read from the device camera_state
        # or from states computed within the GUI code
        self.bind_state_to_proxy("stream_status", camera_state)

    def bind_ai_model_function(self, camera_state: CameraState) -> None:
        # Proxy->State because we want the user to set this value via the GUI
        self.bind_proxy_to_state("ai_model_file", camera_state, Path)

        # State->Proxy because this is computed from the model file
        self.bind_state_to_proxy("ai_model_file_valid", camera_state)

    def bind_firmware_file_functions(self, camera_state: CameraState) -> None:
        # Proxy->State because we want the user to set these values via the GUI
        self.bind_proxy_to_state("firmware_file", camera_state, Path)
        self.bind_proxy_to_state("firmware_file_version", camera_state)
        self.bind_proxy_to_state("firmware_file_type", camera_state)
        # Default value that matches the default widget selection
        self.firmware_file_type = OTAUpdateModule.APFW

        # State->Proxy because these are computed from the firmware_file
        self.bind_state_to_proxy("firmware_file_valid", camera_state)
        self.bind_state_to_proxy("firmware_file_hash", camera_state)

    def bind_input_directories(self, camera_state: CameraState) -> None:
        self.bind_state_to_proxy("image_dir_path", camera_state, str)
        self.bind_state_to_proxy("inference_dir_path", camera_state, str)

    def bind_vapp_file_functions(self, camera_state: CameraState) -> None:
        self.bind_proxy_to_state("vapp_schema_file", camera_state)
        self.bind_proxy_to_state("vapp_config_file", camera_state)
        self.bind_proxy_to_state("vapp_labels_file", camera_state)
        self.bind_proxy_to_state("vapp_type", camera_state)

        # The labels map is computed from the labels file,
        # so data binding must be state-->proxy.
        self.bind_state_to_proxy("vapp_labels_map", camera_state, str)

    def bind_app_module_functions(self, camera_state: CameraState) -> None:
        # State->Proxy because these are either read from the device state
        # or from states computed within the camera tracking
        self.bind_state_to_proxy(
            "deploy_status", camera_state, lambda v: json.dumps(v, indent=4)
        )
        self.bind_state_to_proxy("deploy_stage", camera_state)
        self.bind_state_to_proxy("deploy_operation", camera_state)

        # Proxy->State because we want the user to set this value via the GUI
        self.bind_proxy_to_state("module_file", camera_state, Path)

    def bind_streaming_and_inference(self, camera_state: CameraState) -> None:
        self.bind_state_to_proxy("stream_image", camera_state)
        self.bind_state_to_proxy("inference_field", camera_state)


# Listing of model properties to move over into this class. It is
# derived from the result of the following command, running
# from the repository root:
#
# (cd local-console/src/local_console/gui/model; \
#  ag --py -A1 .setter *.py | ag 'def ' \
#  | sed -e 's,-> None:,,g' -e 's,  def ,,g' \
#        -e 's;self, [^:]*: ;;g' -e 's/-/;/g' \
#  | sort -t';' -k2) > model-properties.csv
#
#   deploy_stage(DeployStage)
#   deploy_status(dict[str, str])
#   manifest(DeploymentManifest)
