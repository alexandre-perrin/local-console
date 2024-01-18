import os
from unittest.mock import patch

import hypothesis.strategies as st
import pytest
from hypothesis import given
from typer.testing import CliRunner
from wedge_cli.commands.start import app
from wedge_cli.commands.start import start_agent
from wedge_cli.utils.enums import Commands
from wedge_cli.utils.enums import config_paths
from wedge_cli.utils.enums import EVPEnvVars
from wedge_cli.utils.schemas import AgentConfiguration
from wedge_cli.utils.schemas import IPAddress
from wedge_cli.utils.schemas import Libraries
from wedge_cli.utils.schemas import RemoteConnectionInfo

from tests.strategies.configs import generate_agent_config
from tests.strategies.configs import generate_valid_ip
from tests.strategies.configs import generate_valid_port_number

runner = CliRunner()


@given(generate_valid_ip(), generate_valid_port_number())
def test_start_remote(remote_host, remote_port) -> None:
    with patch("wedge_cli.commands.start.start_agent") as mock_start_agent:
        result = runner.invoke(app, ["--remote", remote_host, remote_port])
        mock_start_agent.assert_called_once_with(
            connection_info=RemoteConnectionInfo(
                host=IPAddress(ip_value=remote_host), port=remote_port
            ),
            libraries=Libraries(libraries=[]),
        )
        assert result.exit_code == 0


@given(st.lists(st.text(min_size=1, max_size=10), max_size=5, min_size=1))
def test_start_libraries(libraries_list) -> None:
    with patch("wedge_cli.commands.start.start_agent") as mock_start_agent:
        libraries_command = []
        for library in libraries_list:
            libraries_command.append("-l")
            libraries_command.append(library)
        result = runner.invoke(app, libraries_command)
        mock_start_agent.assert_called_once_with(
            connection_info=RemoteConnectionInfo(host=None, port=None),
            libraries=Libraries(libraries=libraries_list),
        )
        assert result.exit_code == 0


@given(generate_agent_config())
def test_start_agent(agent_config: AgentConfiguration) -> None:
    with (
        patch("wedge_cli.commands.start.run") as mock_run_agent,
        patch(
            "wedge_cli.commands.start.get_config", return_value=agent_config
        ) as mock_get_config,
    ):
        start_agent(
            connection_info=RemoteConnectionInfo(host=None, port=None),
            libraries=Libraries(libraries=[]),
        )
        env = os.environ.copy()
        env[EVPEnvVars.EVP_IOT_PLATFORM] = agent_config.evp.iot_platform
        env[EVPEnvVars.EVP_MQTT_HOST] = agent_config.mqtt.host.ip_value
        env[EVPEnvVars.EVP_MQTT_PORT] = str(agent_config.mqtt.port)
        env[EVPEnvVars.EVP_DATA_DIR] = str(config_paths.evp_data_path)  # type:ignore
        env[EVPEnvVars.EVP_HTTPS_CA_CERT] = str(
            config_paths.https_ca_path
        )  # type:ignore
        env[EVPEnvVars.EVP_REPORT_STATUS_INTERVAL_MAX_SEC] = "3"
        env[EVPEnvVars.EVP_MQTT_CLIENTID] = str(agent_config.mqtt.device_id)
        command = [Commands.EVP_AGENT.value]
        mock_run_agent.assert_called_once_with(command, env=env)
        mock_get_config.assert_called_once()


@given(generate_agent_config())
def test_start_agent_file_not_found(agent_config: AgentConfiguration) -> None:
    with (
        patch(
            "wedge_cli.commands.start.run", side_effect=FileNotFoundError
        ) as mock_run_agent,
        patch(
            "wedge_cli.commands.start.get_config", return_value=agent_config
        ) as mock_get_config,
    ):
        with pytest.raises(SystemExit):
            start_agent(
                connection_info=RemoteConnectionInfo(host=None, port=None),
                libraries=Libraries(libraries=[]),
            )
        env = os.environ.copy()
        env[EVPEnvVars.EVP_IOT_PLATFORM] = agent_config.evp.iot_platform
        env[EVPEnvVars.EVP_MQTT_HOST] = agent_config.mqtt.host.ip_value
        env[EVPEnvVars.EVP_MQTT_PORT] = str(agent_config.mqtt.port)
        env[EVPEnvVars.EVP_DATA_DIR] = str(config_paths.evp_data_path)  # type:ignore
        env[EVPEnvVars.EVP_HTTPS_CA_CERT] = str(
            config_paths.https_ca_path
        )  # type:ignore
        env[EVPEnvVars.EVP_REPORT_STATUS_INTERVAL_MAX_SEC] = "3"
        env[EVPEnvVars.EVP_MQTT_CLIENTID] = str(agent_config.mqtt.device_id)
        command = [Commands.EVP_AGENT.value]
        mock_run_agent.assert_called_once_with(command, env=env)
        mock_get_config.assert_called_once()


@given(generate_valid_ip(), generate_valid_port_number())
def test_start_agent_remote(valid_ip: str, port: int) -> None:
    with (
        patch("wedge_cli.commands.start.Listener") as mock_listener,
        patch("wedge_cli.commands.start.run") as mock_run_agent,
        patch("wedge_cli.commands.start.get_config") as mock_get_config,
    ):
        start_agent(
            connection_info=RemoteConnectionInfo(
                host=IPAddress(ip_value=valid_ip), port=port
            ),
            libraries=Libraries(libraries=[]),
        )
        mock_listener.assert_called_once_with(
            ip=IPAddress(ip_value=valid_ip), port=port
        )
        mock_listener.return_value.receive_config.assert_called_once()
        mock_listener.return_value.open_listener.assert_called_once()
        mock_run_agent.assert_called_once()
        mock_get_config.assert_called_once()


@given(
    st.lists(st.text(min_size=1, max_size=10), max_size=5, min_size=1),
    generate_agent_config(),
)
def test_start_agent_libraries(
    libraries_list: list[str], agent_config: AgentConfiguration
) -> None:
    with (
        patch("wedge_cli.commands.start.run") as mock_run_agent,
        patch(
            "wedge_cli.commands.start.get_config", return_value=agent_config
        ) as mock_get_config,
    ):
        start_agent(
            connection_info=RemoteConnectionInfo(host=None, port=None),
            libraries=Libraries(libraries=libraries_list),
        )
        command = [Commands.EVP_AGENT.value]
        libraries_command = []
        for library in libraries_list:
            libraries_command.append("-l")
            libraries_command.append(library)
        env = os.environ.copy()
        env[EVPEnvVars.EVP_IOT_PLATFORM] = agent_config.evp.iot_platform
        env[EVPEnvVars.EVP_MQTT_HOST] = agent_config.mqtt.host.ip_value
        env[EVPEnvVars.EVP_MQTT_PORT] = str(agent_config.mqtt.port)
        env[EVPEnvVars.EVP_DATA_DIR] = str(config_paths.evp_data_path)  # type:ignore
        env[EVPEnvVars.EVP_HTTPS_CA_CERT] = str(
            config_paths.https_ca_path
        )  # type:ignore
        env[EVPEnvVars.EVP_REPORT_STATUS_INTERVAL_MAX_SEC] = "3"
        env[EVPEnvVars.EVP_MQTT_CLIENTID] = str(agent_config.mqtt.device_id)
        command += libraries_command
        mock_run_agent.assert_called_with(command, env=env)
        mock_get_config.assert_called_once()
