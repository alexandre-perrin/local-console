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

from hamcrest.core.base_matcher import BaseMatcher
from hamcrest.core.description import Description


class OTAHasSucceeded(BaseMatcher):
    """
    Example decoded contents of state/backdoor-EA_Main/placeholder:
    {
      "Hardware": {
        "Sensor": "IMX500",
        "SensorId": "100A50500A2012010864012000000000",
        "KG": "1",
        "ApplicationProcessor": "",
        "LedOn": true
      },
      "Version": {
        "SensorFwVersion": "000000",
        "SensorLoaderVersion": "020301",
        "DnnModelVersion": [
          "0308000004830100"
        ],
        "ApFwVersion": "D52408",
        "ApLoaderVersion": "D10300",
        "CameraSetupFileVersion": {
          ...
        }
      },
      "Status": {
        "Sensor": "Standby",
        "ApplicationProcessor": "Idle",
        "SensorTemperature": 34,
        "HoursMeter": 50
      },
      "OTA": {
        "SensorFwLastUpdatedDate": "20240513044609",
        "SensorLoaderLastUpdatedDate": "",
        "DnnModelLastUpdatedDate": [
          "20231128111809"
        ],
        "ApFwLastUpdatedDate": "20240513093441",
        "UpdateProgress": 100,
        "UpdateStatus": "Done"
      },
      "Permission": {
        "FactoryReset": true
      },
      "Image": {
        "FrameRate": 2997,
        "DriveMode": 1
      },
      "Exposure": {
        ...
      },
      "WhiteBalance": {
        ...
      },
      "Adjustment": {
        ...
      },
      "Rotation": {
        "RotAngle": 0
      },
      "Direction": {
        "Vertical": "Normal",
        "Horizontal": "Normal"
      },
      "Network": {
        "ProxyURL": "",
        "ProxyPort": 0,
        "ProxyUserName": "",
        "IPAddress": "",
        "SubnetMask": "",
        "Gateway": "",
        "DNS": "",
        "NTP": "ntp.nict.jp"
      }
    }
    """

    def __init__(self, target_version: str):
        self.target_version = target_version

    def _matches(self, item: str) -> bool:
        obj = self._decode(item)
        return (
            "OTA" in obj
            and "UpdateStatus" in obj["OTA"]
            and "Version" in obj
            and "ApFwVersion" in obj["Version"]
            and obj["Version"]["ApFwVersion"] == self.target_version
            and obj["OTA"]["UpdateStatus"] == "Done"
        )

    def _decode(self, payload: str) -> dict[str, str]:
        obj = json.loads(payload)
        """
        "OTA": {
          "SensorFwLastUpdatedDate": "20240513044609",
          "SensorLoaderLastUpdatedDate": "",
          "DnnModelLastUpdatedDate": [
            "20231128111809"
          ],
          "ApFwLastUpdatedDate": "20240513093441",
          "UpdateProgress": 100,
          "UpdateStatus": "Done"
        },
         "Version": {
           "SensorFwVersion": "000000",
           "SensorLoaderVersion": "020301",
           "DnnModelVersion": ["0308000004830100"],
           "ApFwVersion": "D52408",
           ...
        """
        return obj

    def describe_mismatch(self, item: str, mismatch_description: Description) -> None:
        obj = self._decode(item)

        desc = []
        if "OTA" not in obj:
            desc.append('"OTA" field not part of firmware report')
        if "UpdateStatus" not in obj["OTA"]:
            desc.append('"UpdateStatus" not part of "OTA" report')
        else:
            status = obj["OTA"]["UpdateStatus"]
            if status != "Done":
                desc.append(f'Update status is "{status}" instead of Done')

        if "Version" not in obj:
            desc.append('"Version" field not part of firmware report')
        if "ApFwVersion" not in obj["Version"]:
            desc.append('"ApFwVersion" field not part of "Version" report')
        else:
            fw_ver = obj["Version"]["ApFwVersion"]
            if fw_ver != self.target_version:
                desc.append(
                    f"Firmware version {fw_ver} does not match {self.target_version}"
                )

        if len(desc) == 1:
            reason = desc[0]
        else:
            reason = " and ".join((", ".join(desc[:-1]), desc[-1]))

        mismatch_description.append_text(reason)

    def describe_to(self, description: Description) -> None:
        description.append_text(
            f"reports successful update to version {self.target_version}"
        )


def ota_has_succeeded(target_version: str) -> OTAHasSucceeded:
    return OTAHasSucceeded(target_version)
