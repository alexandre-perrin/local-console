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
from contextlib import contextmanager

from hypothesis import given
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.gui.model.home_screen import HomeScreenModel
from local_console.gui.utils.observer import Observer

from tests.strategies.configs import generate_valid_device_configuration_with_version


class ModelObserver(Observer):
    def __init__(self):
        self.is_called = False

    def model_is_changed(self) -> None:
        self.is_called = True


@contextmanager
def create_model() -> HomeScreenModel:
    model = HomeScreenModel()
    observer = ModelObserver()
    model.add_observer(observer)
    yield model
    assert observer.is_called


def test_initialization():
    model = HomeScreenModel()
    assert not model.device_config
    assert model.sensor_fw_ver == ""
    assert model.sensor_loader_ver == ""
    assert model.app_fw_ver == ""
    assert model.app_loader_ver == ""


@given(generate_valid_device_configuration_with_version())
def test_device_config(device_config: DeviceConfiguration) -> None:
    with create_model() as model:
        model.device_config = None
        assert not model.device_config
        assert model.sensor_fw_ver == ""
        assert model.sensor_loader_ver == ""
        assert model.app_fw_ver == ""
        assert model.app_loader_ver == ""
        model.device_config = device_config
        assert model.device_config
        assert model.sensor_fw_ver == device_config.Version.SensorFwVersion
        assert model.sensor_loader_ver == device_config.Version.SensorLoaderVersion
        assert model.app_fw_ver == device_config.Version.ApFwVersion
        assert model.app_loader_ver == device_config.Version.ApLoaderVersion
