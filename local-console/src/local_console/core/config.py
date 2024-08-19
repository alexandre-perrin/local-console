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
from pathlib import Path
from typing import Optional

from local_console.core.enums import config_paths
from local_console.core.schemas.schemas import DeploymentManifest
from local_console.core.schemas.schemas import DeviceConnection
from local_console.core.schemas.schemas import DeviceListItem
from local_console.core.schemas.schemas import EVPParams
from local_console.core.schemas.schemas import GlobalConfiguration
from local_console.core.schemas.schemas import MQTTParams
from local_console.core.schemas.schemas import Persist
from local_console.core.schemas.schemas import WebserverParams
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """
    Used for conveying error messages in a framework-agnostic way
    """


def optional_path(path: Optional[str]) -> Optional[Path]:
    return Path(path) if path else None


class Config:
    def __init__(self) -> None:
        self._config = self.get_default_config()

    @property
    def config(self) -> GlobalConfiguration:
        return self._config

    @staticmethod
    def get_default_config() -> GlobalConfiguration:
        return GlobalConfiguration(
            evp=EVPParams(iot_platform="EVP1"),
            devices=[
                Config._create_device_config(DeviceListItem(name="Default", port=1883))
            ],
            active_device=1883,
        )

    def read_config(self) -> bool:
        """
        Reads the configuration from disk.

        If the file is not found, it returns False.
        """
        if not config_paths.config_path.is_file():
            logger.warning("Config file not found")
            return False

        try:
            with open(config_paths.config_path) as f:
                self._config = GlobalConfiguration(**json.load(f))
            return True
        except Exception as e:
            raise ConfigError(f"Config file not well formed: {e}")

    def save_config(self) -> None:
        logger.info("Storing configuration")
        config_path = config_paths.config_path
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, "w") as f:
                f.write(self._config.model_dump_json(indent=2))
        except Exception as e:
            raise ConfigError(
                f"Error while generating folder {config_path.parent} or storing configuration: {e}"
            )

    def get_config(self) -> GlobalConfiguration:
        return self._config

    def get_device_config(self, key: int) -> DeviceConnection:
        for device_config in self._config.devices:
            if device_config.mqtt.port == key:
                return device_config
        raise ConfigError(f"Device for port {key} not found")

    def get_device_config_by_name(self, name: str) -> DeviceConnection:
        for device_config in self._config.devices:
            if device_config.name == name:
                return device_config
        raise ConfigError(f"Device named '{name}' not found")

    def get_active_device_config(self) -> DeviceConnection:
        if len(self._config.devices) == 1:
            active_device = self._config.devices[0]
        else:
            gather = [
                device
                for device in self._config.devices
                if device.mqtt.port == self._config.active_device
            ]
            assert len(gather) == 1
            active_device = gather[0]

        return active_device

    def rename_entry(self, port: int, new_name: str) -> None:
        entry: DeviceConnection = next(
            d for d in self._config.devices if d.mqtt.port == port
        )
        entry.name = new_name
        self.save_config()

    def get_deployment(self) -> DeploymentManifest:
        try:
            with open(config_paths.deployment_json) as f:
                deployment_data = json.load(f)
        except Exception:
            raise ConfigError("deployment.json does not exist or is not well formed")
        try:
            return DeploymentManifest(**deployment_data)
        except ValidationError as e:
            missing_field = list(e.errors()[0]["loc"])[1:]
            raise ConfigError(
                f"Missing field in the deployment manifest: {missing_field}"
            )

    def construct_device_record(self, device_item: DeviceListItem) -> DeviceConnection:
        record_lookup = (
            dev for dev in self.config.devices if dev.mqtt.port == device_item.port
        )
        conn = next(record_lookup, None)
        if conn is None:
            conn = self._create_device_config(device_item)

        return conn

    def commit_device_record(self, device_conn: DeviceConnection) -> None:
        record_lookup = (
            dev for dev in self.config.devices if dev.mqtt.port == device_conn.mqtt.port
        )
        if next(record_lookup, None) is None:
            self._config.devices.append(device_conn)

    def remove_device(self, key: int) -> None:
        self._config.devices = [
            connection
            for connection in self._config.devices
            if connection.mqtt.port != key
        ]

    def get_device_configs(self) -> list[DeviceConnection]:
        return self._config.devices

    def get_device_list_items(self) -> list[DeviceListItem]:
        return [
            DeviceListItem(name=device.name, port=device.mqtt.port)
            for device in self._config.devices
        ]

    @staticmethod
    def _create_device_config(device: DeviceListItem) -> DeviceConnection:
        return DeviceConnection(
            mqtt=MQTTParams(
                host="localhost",
                port=device.port,
                device_id=None,
            ),
            webserver=WebserverParams(
                host="localhost",
                port=0,
            ),
            name=device.name,
            persist=Persist(),
        )


# TODO:FIXME: do not use global variable
config_obj = Config()

# alias for backward compatibility


def get_config() -> GlobalConfiguration:
    return config_obj.get_config()
