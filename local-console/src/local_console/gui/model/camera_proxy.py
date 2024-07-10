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
from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty
from kivy.properties import ObjectProperty
from kivy.properties import StringProperty
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration


class CameraStateProxy(EventDispatcher):

    is_ready = BooleanProperty(False)
    is_streaming = BooleanProperty(False)
    image_dir_path = StringProperty("")
    inference_dir_path = StringProperty("")

    device_config = ObjectProperty(DeviceConfiguration, allownone=True)


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
#   image_directory(Optional[Path])
#   inferences_directory(Optional[Path])
#   stream_status(StreamStatus)
#   stream_status(StreamStatus)
#   app_configuration(Optional[str])
#   app_labels(Optional[str])
#   app_type(Optional[str])
#   connected(bool)
#   deploy_stage(DeployStage)
#   deploy_status(dict[str, str])
#   dns_server(str)
#   downloading_progress(int)
#   firmware_file_hash(str)
#   firmware_file(Path)
#   firmware_file_type(str)
#   firmware_file_valid(bool)
#   firmware_file_version(str)
#   flatbuffers_process_result(Optional[str])
#   flatbuffers_schema(Optional[Path])
#   flatbuffers_schema_status(bool)
#   gateway(str)
#   image_roi(UnitROI)
#   ip_address(str)
#   local_ip(str)
#   manifest(DeploymentManifest)
#   model_file(Path)
#   mqtt_host(str)
#   mqtt_port(str)
#   ntp_host(str)
#   subnet_mask(str)
#   update_status(str)
#   updating_progress(int)
#   warning_message(str)
#   wifi_icon_eye(str)
#   wifi_password_hidden(bool)
#   wifi_password(str)
#   wifi_ssid(str)
