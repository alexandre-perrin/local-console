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
import configparser
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from local_console.core.config import ConfigError
from local_console.core.schemas.schemas import AgentConfiguration
from local_console.core.schemas.schemas import DeviceListItem


app_subdir = Path("local-console")
dummy_home = Path("/tmp/test_devices")
dummy_default_home = dummy_home / ".config" / app_subdir
dummy_config_path = dummy_default_home / "config.ini"


@pytest.fixture(scope="module", autouse=True)
def cleanup_config():
    with (patch("local_console.core.config.config_paths") as mock_config_paths,):
        mock_config_paths.config_path = dummy_config_path
        yield

        if dummy_home.is_dir:
            shutil.rmtree(dummy_home)


def test_set_default_config_error():
    err_msg = "Mock error"
    with (
        patch("builtins.open", side_effect=OSError(err_msg)),
        pytest.raises(
            ConfigError,
            match=f"Error while generating folder {dummy_default_home}: {err_msg}",
        ),
    ):
        from local_console.core.config import setup_default_config

        setup_default_config()


def test_config_to_schema_error():
    with pytest.raises(
        ConfigError,
        match="Config file not correct. Section or parameter missing is",
    ):
        config_parser: configparser.ConfigParser = configparser.ConfigParser()
        from local_console.core.config import config_to_schema

        config_to_schema(config_parser)


def test_get_config_file_not_found():
    with (
        patch("configparser.ConfigParser.read", side_effect=FileNotFoundError()),
        pytest.raises(
            ConfigError,
            match="Config file not found",
        ),
    ):
        from local_console.core.config import get_config

        get_config()


def test_get_config_missing_section():
    with (
        patch(
            "configparser.ConfigParser.read",
            side_effect=configparser.MissingSectionHeaderError("dumy", 1, "1"),
        ),
        pytest.raises(
            ConfigError,
            match="No header found in the specified file",
        ),
    ):
        from local_console.core.config import get_config

        get_config()


def test_get_deployment_schema_error():
    with (
        patch("builtins.open", side_effect=Exception),
        pytest.raises(
            ConfigError,
            match="deployment.json does not exist or is not well formed",
        ),
    ):
        from local_console.core.config import get_deployment_schema

        get_deployment_schema()


def test_check_section_and_params_error_section():
    from local_console.core.config import setup_default_config
    from local_console.core.config import get_config

    setup_default_config()
    agent_config: AgentConfiguration = get_config()

    with (
        pytest.raises(
            ConfigError,
            match="Invalid section. Valid ones are: ",
        ),
    ):
        from local_console.core.config import check_section_and_params

        check_section_and_params(agent_config, "test")


def test_check_section_and_params_error_param():
    from local_console.core.config import get_config

    agent_config: AgentConfiguration = get_config()

    with (
        pytest.raises(
            ConfigError,
            match="Invalid parameter of the mqtt section. Valid ones are:",
        ),
    ):
        from local_console.core.config import check_section_and_params

        check_section_and_params(agent_config, "mqtt", "test")


def test_add_device_to_config():
    with (
        patch("configparser.ConfigParser.write", side_effect=OSError("mock error")),
        pytest.raises(
            ConfigError,
            match="Error: mock error",
        ),
    ):
        from local_console.core.config import add_device_to_config

        device = DeviceListItem(name="test_device", port="1234")
        add_device_to_config(device)


def test_mkdir_with_device_config_file_not_found():
    with (
        patch("configparser.ConfigParser.read", side_effect=FileNotFoundError),
        pytest.raises(
            ConfigError,
            match="Config file not found",
        ),
    ):
        from local_console.core.config import get_global_config

        get_global_config()


def test_mkdir_with_device_config_error():
    with (
        patch(
            "configparser.ConfigParser.read",
            side_effect=configparser.MissingSectionHeaderError("dumy", 1, "1"),
        ),
        pytest.raises(
            ConfigError,
            match="No header found in the specified file",
        ),
    ):
        from local_console.core.config import get_global_config

        get_global_config()


def test_create_device_config_error():
    with (pytest.raises(ConfigError, match="ValidationError: "),):
        from local_console.core.config import create_device_config

        device = DeviceListItem(name="test_device ##222222222", port="1234")
        create_device_config(device)


def test_remove_device_config_error():
    if dummy_home.is_dir:
        shutil.rmtree(dummy_home)

    from local_console.core.config import setup_default_config
    from local_console.core.config import add_device_to_config

    setup_default_config()

    device = DeviceListItem(name="test_device", port="1234")
    add_device_to_config(device)

    with (
        patch(
            "configparser.ConfigParser.write",
            side_effect=OSError,
        ),
        pytest.raises(ConfigError, match="Error: "),
    ):
        from local_console.core.config import remove_device_config

        remove_device_config(device.name)
