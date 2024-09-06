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
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from local_console.core.camera.enums import OTAUpdateModule
from local_console.core.camera.firmware import validate_firmware_file
from local_console.core.commands.ota_deploy import get_package_hash
from local_console.core.schemas.edge_cloud_if_v1 import DeviceConfiguration
from local_console.core.schemas.edge_cloud_if_v1 import DnnOta
from local_console.core.schemas.edge_cloud_if_v1 import DnnOtaBody
from local_console.core.schemas.edge_cloud_if_v1 import Hardware
from local_console.core.schemas.edge_cloud_if_v1 import OTA
from local_console.core.schemas.edge_cloud_if_v1 import Permission
from local_console.core.schemas.edge_cloud_if_v1 import Status
from local_console.core.schemas.edge_cloud_if_v1 import Version

from tests.fixtures.camera import cs_init
from tests.fixtures.gui import driver_set


@pytest.fixture(params=["Application Firmware", "Sensor Firmware"])
def firmware_type(request):
    return request.param


@pytest.fixture(params=["Done", "Failed"])
def update_status(request):
    return request.param


def device_config(UpdateProgress, UpdateStatus):
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


@pytest.mark.trio
async def test_select_path(driver_set, tmp_path, cs_init) -> None:
    """
    Test how selection of file path and type results in
    hash computation and determining validity of the file,
    both in the state variables and proxy properties.
    """

    driver, mock_gui = driver_set
    driver.camera_state = cs_init
    state = driver.camera_state
    mock_gui.mdl.bind_firmware_file_functions(state)

    app_fw_filename = "ota.bin"
    app_fw_file_path = tmp_path / app_fw_filename
    sensor_fw_filename = "firmware.fpk"
    sensor_fw_file_path = tmp_path / sensor_fw_filename

    # Create dummy firmware files and hashes
    app_fw_file_path.write_text("dummy")
    app_fw_file_hash = get_package_hash(app_fw_file_path)

    sensor_fw_file_path.write_text("foobar")
    sensor_fw_file_hash = get_package_hash(sensor_fw_file_path)

    # Select Application Firmware
    state.firmware_file.value = app_fw_file_path
    assert state.firmware_file_hash.value == app_fw_file_hash
    assert mock_gui.mdl.firmware_file_hash == app_fw_file_hash

    assert state.firmware_file_valid.value
    assert mock_gui.mdl.firmware_file_valid

    # Switch path to not match its type
    state.firmware_file.value = sensor_fw_file_path
    assert not state.firmware_file_valid.value
    assert not mock_gui.mdl.firmware_file_valid

    # Select Sensor Firmware
    state.firmware_file_type.value = OTAUpdateModule.SENSORFW
    state.firmware_file.value = sensor_fw_file_path

    assert state.firmware_file_hash.value == sensor_fw_file_hash
    assert mock_gui.mdl.firmware_file_hash == sensor_fw_file_hash

    assert state.firmware_file_valid.value
    assert mock_gui.mdl.firmware_file_valid

    # Switch path to not match its type
    state.firmware_file.value = app_fw_file_path
    assert not state.firmware_file_valid.value
    assert not mock_gui.mdl.firmware_file_valid


def test_validate_firmware_file(tmp_path):
    """
    Test how selection of file path and type results in
    hash computation and determining validity of the file,
    both in the state variables and proxy properties.
    """
    from local_console.core.camera.firmware import FirmwareException

    # Create dummy firmware files
    app_fw_file_path = tmp_path / "ota.bin"
    app_fw_file_path.write_text("dummy")
    sensor_fw_file_path = tmp_path / "firmware.fpk"
    sensor_fw_file_path.write_text("foobar")

    # For firmware validation, update report values in device config are irrelevant
    a_config = device_config(-1, "irrelevant")

    # Check what happens when passing an inexistent file
    inexistent_file = tmp_path / "i_dont_exist"
    assert not inexistent_file.exists()
    with pytest.raises(FirmwareException, match="Firmware file does not exist!"):
        validate_firmware_file(
            inexistent_file, OTAUpdateModule.APFW, "", current_cfg=a_config
        )

    # Check what happens when device configuration is not available
    with (patch("local_console.core.camera.firmware.logger") as mock_logger,):
        assert not validate_firmware_file(
            app_fw_file_path, OTAUpdateModule.APFW, "", current_cfg=None
        )
        mock_logger.debug.assert_called_once_with("DeviceConfiguration is None.")

    # Test Application Firmware on mismatched file with the set type
    with pytest.raises(FirmwareException, match="Invalid Application Firmware!"):
        validate_firmware_file(
            sensor_fw_file_path, OTAUpdateModule.APFW, "irrelevant", a_config
        )

    # Test matching file and type and version equal to a_config.Version.ApFwVersion
    with pytest.raises(
        FirmwareException, match="Version is the same as the current firmware."
    ):
        version = a_config.Version.ApFwVersion
        validate_firmware_file(
            app_fw_file_path, OTAUpdateModule.APFW, version, a_config
        )

    # Test matching file and type and a different version
    assert validate_firmware_file(
        app_fw_file_path, OTAUpdateModule.APFW, "D700T0", a_config
    )

    # Test Sensor Firmware on mismatched file with the set type
    with pytest.raises(FirmwareException, match="Invalid Sensor Firmware!"):
        validate_firmware_file(
            app_fw_file_path, OTAUpdateModule.SENSORFW, "irrelevant", a_config
        )

    # Test matching file and type and version equal to a_config.Version.ApFwVersion
    with pytest.raises(
        FirmwareException, match="Version is the same as the current firmware."
    ):
        version = a_config.Version.SensorFwVersion
        validate_firmware_file(
            sensor_fw_file_path, OTAUpdateModule.SENSORFW, version, a_config
        )

    # Test matching file and type and a different version
    assert validate_firmware_file(
        sensor_fw_file_path, OTAUpdateModule.SENSORFW, "010300", a_config
    )


def test_progress_update_checkpoint():

    from local_console.core.camera.firmware import progress_update_checkpoint
    from local_console.core.camera.firmware import TransientStatus
    from local_console.gui.view.firmware_screen.firmware_screen import (
        FirmwareTransientStatus,
    )

    for indicator_class in (TransientStatus, FirmwareTransientStatus):
        indicator = indicator_class()

        assert not progress_update_checkpoint(
            device_config(0, "Downloading"), indicator
        )
        assert indicator.progress_download == 0
        assert indicator.progress_update == 0

        assert not progress_update_checkpoint(
            device_config(75, "Downloading"), indicator
        )
        assert indicator.progress_download == 75
        assert indicator.progress_update == 0

        assert not progress_update_checkpoint(device_config(25, "Updating"), indicator)
        assert indicator.progress_download == 100
        assert indicator.progress_update == 25

        assert not progress_update_checkpoint(
            device_config(100, "Rebooting"), indicator
        )
        assert indicator.progress_download == 100
        assert indicator.progress_update == 100

        assert progress_update_checkpoint(device_config(100, "Done"), indicator)
        assert indicator.progress_download == 100
        assert indicator.progress_update == 100

        assert progress_update_checkpoint(device_config(75, "Failed"), indicator)


@pytest.mark.trio
async def test_update_firmware_task_invalid(tmp_path, cs_init) -> None:

    from local_console.core.camera.firmware import update_firmware_task

    from local_console.core.camera.firmware import TransientStatus
    from local_console.core.camera.firmware import FirmwareException

    camera_state = cs_init
    indicator = TransientStatus()
    error_notify = Mock()
    with (
        patch.object(camera_state, "ota_event") as mock_ota_event,
        patch(
            "local_console.core.camera.firmware.validate_firmware_file",
            side_effect=FirmwareException("invalid file"),
        ),
    ):
        # Pretend these values are meaningful
        camera_state.firmware_file.value = tmp_path / "some file"
        camera_state.firmware_file_type.value = "some type"
        camera_state.firmware_file_version.value = "some version"

        await update_firmware_task(camera_state, indicator, error_notify)
        mock_ota_event.assert_not_awaited()
        error_notify.assert_called_once_with("invalid file")


@pytest.mark.trio
@pytest.mark.parametrize(
    "ota_type",
    ["ApFw", "SensorFw"],
)
async def test_update_firmware_task_valid(tmp_path, cs_init, ota_type) -> None:

    from local_console.core.camera.firmware import update_firmware_task

    from local_console.core.camera.firmware import TransientStatus
    from local_console.core.camera.enums import OTAUpdateModule

    camera_state = cs_init

    indicator = TransientStatus()
    error_notify = Mock()

    extension = "bin" if ota_type == "ApFw" else "fpk"
    filename = f"dummy_ota.{extension}"
    app_fw_file_path = tmp_path / filename
    app_fw_file_path.write_text("dummy")
    camera_state.firmware_file.value = app_fw_file_path
    camera_state.firmware_file_type.value = OTAUpdateModule(ota_type)
    camera_state.firmware_file_version.value = "ABCDEF"

    # Set the end state
    camera_state.device_config.value = device_config(100, "Done")

    mock_agent = MagicMock()
    mock_agent.mqtt_scope.return_value = AsyncMock()
    mock_agent.configure = AsyncMock()

    mock_server = AsyncMock()
    mock_server.__aenter__.return_value.port = 8000

    hashvalue = get_package_hash(app_fw_file_path)
    payload = DnnOta(
        OTA=DnnOtaBody(
            UpdateModule=ota_type,
            DesiredVersion=camera_state.firmware_file_version.value,
            PackageUri=f"http://1.1.1.1:8000/{filename}",
            HashValue=hashvalue,
        )
    ).model_dump_json()

    with (
        patch.object(camera_state, "ota_event") as mock_ota_event,
        patch("local_console.core.camera.firmware.Agent", return_value=mock_agent),
        patch(
            "local_console.core.camera.firmware.AsyncWebserver",
            return_value=mock_server,
        ),
        patch(
            "local_console.core.camera.firmware.get_webserver_ip",
            return_value="1.1.1.1",
        ),
    ):
        await update_firmware_task(camera_state, indicator, error_notify)

        mock_agent.configure.assert_awaited_once_with(
            "backdoor-EA_Main", "placeholder", payload
        )
        mock_ota_event.assert_awaited_once_with()
        error_notify.assert_not_called()
        assert indicator.progress_download == 100
        assert indicator.progress_update == 100
        assert indicator.update_status == "Done"
