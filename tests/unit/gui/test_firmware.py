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
from pathlib import Path
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from hypothesis import given
from local_console.core.commands.ota_deploy import get_package_hash
from local_console.core.config import config_to_schema
from local_console.core.config import get_default_config
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.edge_cloud_if_v1 import Hardware
from local_console.core.schemas.edge_cloud_if_v1 import OTA
from local_console.core.schemas.edge_cloud_if_v1 import Permission
from local_console.core.schemas.edge_cloud_if_v1 import Status
from local_console.core.schemas.edge_cloud_if_v1 import Version
from local_console.gui.controller.firmware_screen import FirmwareScreenController
from local_console.gui.enums import FirmwareType
from local_console.gui.enums import OTAUpdateModule
from local_console.gui.model.firmware_screen import FirmwareScreenModel
from local_console.gui.utils.observer import Observer
from local_console.utils.local_network import get_my_ip_by_routing

from tests.strategies.configs import generate_text


def mock_get_config():
    return config_to_schema(get_default_config())


@pytest.fixture(autouse=True)
def fixture_get_config():
    with patch(
        "local_console.gui.controller.firmware_screen.get_config",
        mock_get_config,
    ) as _fixture:
        yield _fixture


@pytest.fixture(params=["Application Firmware", "Sensor Firmware"])
def firmware_type(request):
    return request.param


@pytest.fixture(params=["Done", "Failed"])
def update_status(request):
    return request.param


def device_config_template(UpdateProgress, UpdateStatus):
    return DeviceConfiguration(
        Hardware=Hardware(
            Sensor="", SensorId="", KG="", ApplicationProcessor="", LedOn=True
        ),
        Version=Version(
            SensorFwVersion="010707",
            SensorLoaderVersion="020301",
            DnnModelVersion=[],
            ApFwVersion="D52408",
            ApLoaderVersion="D10300",
        ),
        Status=Status(Sensor="", ApplicationProcessor=""),
        OTA=OTA(
            SensorFwLastUpdatedDate="",
            SensorLoaderLastUpdatedDate="",
            DnnModelLastUpdatedDate=[],
            ApFwLastUpdatedDate="",
            UpdateProgress=UpdateProgress,
            UpdateStatus=UpdateStatus,
        ),
        Permission=Permission(FactoryReset=False),
    )


@pytest.fixture()
def device_config():
    return device_config_template(100, "Done")


class ModelObserver(Observer):
    def __init__(self):
        self.is_called = False

    def model_is_changed(self) -> None:
        self.is_called = True


@contextmanager
def create_model() -> FirmwareScreenModel:
    model = FirmwareScreenModel()
    observer = ModelObserver()
    model.add_observer(observer)
    yield model
    assert observer.is_called


def test_get_view():
    with patch("local_console.gui.controller.firmware_screen.FirmwareScreenView"):
        controller = FirmwareScreenController(MagicMock(), MagicMock())
        assert controller.view == controller.get_view()


def test_initialization():
    model = FirmwareScreenModel()
    assert model.device_config is None
    assert model.firmware_file == Path()
    assert model.firmware_file_valid is False
    assert model.firmware_file_type == OTAUpdateModule.APFW
    assert model.firmware_file_version == ""
    assert model.firmware_file_hash == ""
    assert model.downloading_progress == 0
    assert model.updating_progress == 0
    assert model.update_status == ""


@pytest.mark.trio
async def test_device_config(device_config: DeviceConfiguration):
    model = FirmwareScreenModel()
    observer = ModelObserver()
    model.add_observer(observer)

    model.device_config = None
    assert not observer.is_called
    model.device_config = device_config
    assert observer.is_called
    assert model._device_config_previous == device_config


def test_select_path(tmp_path):
    app_fw_filename = "ota.bin"
    app_fw_file_path = tmp_path / app_fw_filename
    sensor_fw_filename = "firmware.fpk"
    sensor_fw_file_path = tmp_path / sensor_fw_filename
    mock_driver = MagicMock()
    with create_model() as model:
        with patch("local_console.gui.controller.firmware_screen.FirmwareScreenView"):
            controller = FirmwareScreenController(model, mock_driver)

            # Create dummy firmware files
            with open(app_fw_file_path, "w") as f:
                f.write("dummy")

            with open(sensor_fw_file_path, "w") as f:
                f.write("dummy")

            # Application Firmware
            controller.select_path(app_fw_file_path)
            assert model.firmware_file == app_fw_file_path
            assert model.firmware_file_hash == get_package_hash(app_fw_file_path)
            assert model.firmware_file_valid

            controller.select_path(sensor_fw_file_path)
            assert not model.firmware_file_valid

            # Select Sensor Firmware
            model.firmware_file_type = OTAUpdateModule.SENSORFW
            controller.select_path(sensor_fw_file_path)
            assert model.firmware_file == sensor_fw_file_path
            assert model.firmware_file_hash == get_package_hash(sensor_fw_file_path)
            assert model.firmware_file_valid

            controller.select_path(app_fw_file_path)
            assert not model.firmware_file_valid


def test_select_firmware_type():
    mock_driver = MagicMock()
    with create_model() as model:
        with patch("local_console.gui.controller.firmware_screen.FirmwareScreenView"):
            controller = FirmwareScreenController(model, mock_driver)
            assert model.firmware_file_type == OTAUpdateModule.APFW
            controller.select_firmware_type(FirmwareType.APPLICATION_FW)
            assert model.firmware_file_type == OTAUpdateModule.APFW
            controller.select_firmware_type(FirmwareType.SENSOR_FW)
            assert model.firmware_file_type == OTAUpdateModule.SENSORFW


@given(generate_text())
def test_set_firmware_version(version: str):
    mock_driver = MagicMock()
    with create_model() as model:
        with patch("local_console.gui.controller.firmware_screen.FirmwareScreenView"):
            controller = FirmwareScreenController(model, mock_driver)
            controller.set_firmware_version(version)
            assert model.firmware_file_version == version


def test_update_firmware():
    mock_driver = MagicMock()
    model = FirmwareScreenModel()
    with (
        patch("local_console.gui.controller.firmware_screen.FirmwareScreenView"),
        patch("local_console.gui.controller.firmware_screen.logger") as mock_logger,
    ):
        controller = FirmwareScreenController(model, mock_driver)
        controller.view.ids.btn_update_firmware.disabled = False
        controller.update_firmware()
        assert controller.view.ids.btn_update_firmware.disabled

        controller.view.ids.btn_update_firmware.disabled = True
        controller.update_firmware()
        mock_logger.warning.assert_called_once_with(
            "The firmware update button is disabled"
        )


def test_validate_firmware_file(tmp_path, device_config):
    app_fw_filename = "ota.bin"
    app_fw_file_path = tmp_path / app_fw_filename
    sensor_fw_filename = "firmware.fpk"
    sensor_fw_file_path = tmp_path / sensor_fw_filename
    mock_driver = MagicMock()
    model = FirmwareScreenModel()
    with (
        patch("local_console.gui.controller.firmware_screen.FirmwareScreenView"),
        patch("local_console.gui.controller.firmware_screen.logger") as mock_logger,
    ):
        controller = FirmwareScreenController(model, mock_driver)

        firmware_file = None
        assert not controller.validate_firmware_file(firmware_file)

        firmware_file = MagicMock()
        firmware_file.resolve.return_value = False
        assert not controller.validate_firmware_file(firmware_file)

        # Create dummy firmware files
        with open(app_fw_file_path, "w") as f:
            f.write("dummy")

        with open(sensor_fw_file_path, "w") as f:
            f.write("dummy")

        assert not controller.validate_firmware_file(app_fw_file_path)
        mock_logger.debug.assert_called_once_with("DeviceConfiguration is None.")

        model.device_config = device_config

        # Select Application Firmware
        assert not controller.validate_firmware_file(sensor_fw_file_path)
        model.firmware_file_version = "D52408"
        assert not controller.validate_firmware_file(app_fw_file_path)
        model.firmware_file_version = "D700T0"
        assert controller.validate_firmware_file(app_fw_file_path)

        # Select Sensor Firmware
        model.firmware_file_type = OTAUpdateModule.SENSORFW
        assert not controller.validate_firmware_file(app_fw_file_path)
        model.firmware_file_version = "010707"
        assert not controller.validate_firmware_file(sensor_fw_file_path)
        model.firmware_file_version = "010300"
        assert controller.validate_firmware_file(sensor_fw_file_path)


def test_update_progress_bar():
    mock_driver = MagicMock()
    model = FirmwareScreenModel()
    with patch("local_console.gui.controller.firmware_screen.FirmwareScreenView"):
        controller = FirmwareScreenController(model, mock_driver)

        device_config_previous = model.device_config

        assert not controller.update_progress_bar(device_config_previous)
        assert model.downloading_progress == 0
        assert model._updating_progress == 0

        model.device_config = device_config_template(75, "Downloading")
        assert not controller.update_progress_bar(device_config_previous)
        assert model.downloading_progress == 75
        assert model._updating_progress == 0

        model.device_config = device_config_template(25, "Updating")
        assert not controller.update_progress_bar(device_config_previous)
        assert model.downloading_progress == 100
        assert model._updating_progress == 25

        model.device_config = device_config_template(100, "Rebooting")
        assert not controller.update_progress_bar(device_config_previous)
        assert model.downloading_progress == 100
        assert model._updating_progress == 100

        model.device_config = device_config_template(100, "Done")
        assert controller.update_progress_bar(device_config_previous)
        assert model.downloading_progress == 100
        assert model._updating_progress == 100

        model.device_config = device_config_template(75, "Failed")
        assert controller.update_progress_bar(device_config_previous)


@pytest.mark.trio
async def test_update_firmware_task_invalid_firmware_file(tmp_path):
    app_fw_filename = "ota.bin"
    app_fw_file_path = tmp_path / app_fw_filename
    sensor_fw_filename = "firmware.fpk"
    sensor_fw_file_path = tmp_path / sensor_fw_filename

    mock_driver = MagicMock()
    model = FirmwareScreenModel()
    with (
        patch("local_console.gui.controller.firmware_screen.FirmwareScreenView"),
        patch("local_console.gui.controller.firmware_screen.logger") as mock_logger,
    ):
        controller = FirmwareScreenController(model, mock_driver)

        # Create dummy firmware files
        with open(app_fw_file_path, "w") as f:
            f.write("dummy")

        with open(sensor_fw_file_path, "w") as f:
            f.write("dummy")

        model.firmware_file_type = OTAUpdateModule.APFW
        model.device_config = device_config_template(100, "Done")
        await controller.update_firmware_task(sensor_fw_file_path)
        mock_logger.warning.assert_called_once_with("Firmware file is not valid.")


@pytest.mark.trio
async def test_update_firmware_task(tmp_path):
    app_fw_filename = "dummy_ota.bin"
    app_fw_file_path = tmp_path / app_fw_filename
    sensor_fw_filename = "dummy_firmware.fpk"
    sensor_fw_file_path = tmp_path / sensor_fw_filename

    mock_driver = MagicMock()
    model = FirmwareScreenModel()
    model.ota_event = AsyncMock()
    mock_agent = MagicMock()
    mock_agent.mqtt_scope.return_value = AsyncMock()
    mock_agent.configure = AsyncMock()
    with (
        patch("local_console.gui.controller.firmware_screen.FirmwareScreenView"),
        patch(
            "local_console.gui.controller.firmware_screen.Agent",
            return_value=mock_agent,
        ),
        patch(
            "local_console.gui.controller.firmware_screen.AsyncWebserver",
            return_value=mock_agent,
        ),
        patch(
            "local_console.gui.controller.firmware_screen.FirmwareScreenController.update_progress_bar",
            return_value=True,
        ),
    ):
        controller = FirmwareScreenController(model, mock_driver)

        # Create dummy firmware files
        with open(app_fw_file_path, "w") as f:
            f.write("dummy")

        with open(sensor_fw_file_path, "w") as f:
            f.write("dummy")

        model.device_config = device_config_template(100, "Done")
        model.firmware_file_version = "D700T0"

        await controller.update_firmware_task(app_fw_file_path)
        hashvalue = get_package_hash(app_fw_file_path)
        payload = (
            '{"OTA":{"UpdateModule":"ApFw","DesiredVersion":"D700T0",'
            f'"PackageUri":"http://{get_my_ip_by_routing()}:8000/dummy_ota.bin",'
            f'"HashValue":"{hashvalue}"'
            "}}"
        )
        mock_agent.configure.assert_called_once_with(
            "backdoor-EA_Main", "placeholder", payload
        )
        model.ota_event.assert_not_awaited()
