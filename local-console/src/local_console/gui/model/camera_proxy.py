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
from kivy.properties import BooleanProperty
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
from local_console.core.camera import OTAUpdateModule
from local_console.core.camera.axis_mapping import DEFAULT_ROI
from local_console.core.camera.enums import StreamStatus
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.gui.model.data_binding import CameraStateProxyBase


class CameraStateProxy(CameraStateProxyBase):

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

    firmware_file = StringProperty("", allownone=True)
    firmware_file_valid = BooleanProperty(False, force_dispatch=True)
    firmware_file_version = StringProperty("", allownone=True)
    firmware_file_type = ObjectProperty(OTAUpdateModule, allownone=True)
    firmware_file_hash = StringProperty("", allownone=True)


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
#   app_configuration(Optional[str])
#   app_labels(Optional[str])
#   app_type(Optional[str])
#   connected(bool)
#   deploy_stage(DeployStage)
#   deploy_status(dict[str, str])
#   dns_server(str)
#   flatbuffers_schema(Optional[Path])
#   flatbuffers_schema_status(bool)
#   gateway(str)
#   ip_address(str)
#   local_ip(str)
#   manifest(DeploymentManifest)
#   mqtt_host(str)
#   mqtt_port(str)
#   ntp_host(str)
#   subnet_mask(str)
#   warning_message(str)
#   wifi_icon_eye(str)
#   wifi_password_hidden(bool)
#   wifi_password(str)
#   wifi_ssid(str)
