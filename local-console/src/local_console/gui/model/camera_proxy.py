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
from pathlib import Path

from kivy.properties import BooleanProperty
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
from local_console.core.camera.axis_mapping import DEFAULT_ROI
from local_console.core.camera.enums import DeployStage
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.enums import StreamStatus
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
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

    vapp_schema_file = ObjectProperty(Path(), allownone=True)
    vapp_config_file = ObjectProperty(Path(), allownone=True)
    vapp_labels_file = ObjectProperty(Path(), allownone=True)
    vapp_labels_map = ObjectProperty({}, allownone=True)
    vapp_type = StringProperty("")

    firmware_file = StringProperty("", allownone=True)
    firmware_file_valid = BooleanProperty(False, force_dispatch=True)
    firmware_file_version = StringProperty("", allownone=True)
    firmware_file_type = ObjectProperty(OTAUpdateModule, allownone=True)
    firmware_file_hash = StringProperty("", allownone=True)

    local_ip = StringProperty("")
    mqtt_host = StringProperty("")
    mqtt_port = StringProperty("")
    ntp_host = StringProperty("")
    ip_address = StringProperty("")
    subnet_mask = StringProperty("")
    gateway = StringProperty("")
    dns_server = StringProperty("")
    wifi_ssid = StringProperty("")
    wifi_password = StringProperty("")
    wifi_password_hidden = BooleanProperty(True, force_dispatch=True)
    wifi_icon_eye = StringProperty("")

    module_file = StringProperty("", allownone=True)
    deploy_status = ObjectProperty(dict(), allownone=True)
    deploy_stage = ObjectProperty(DeployStage, allownone=True)

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
