from unittest.mock import patch
from uuid import UUID

import hypothesis.strategies as st
from hypothesis import given
from typer.testing import CliRunner
from wedge_cli.commands.start import app
from wedge_cli.commands.start import start_agent
from wedge_cli.utils.enums import Commands
from wedge_cli.utils.enums import config_paths
from wedge_cli.utils.enums import EVPEnvVars
from wedge_cli.core.schemas import AgentConfiguration
from wedge_cli.core.schemas import IPAddress
from wedge_cli.core.schemas import Libraries
from wedge_cli.core.schemas import RemoteConnectionInfo
from wedge_cli.core.schemas import TLSConfiguration

from tests.strategies.configs import generate_agent_config
from tests.strategies.configs import generate_tls_config
from tests.strategies.configs import generate_valid_ip
from tests.strategies.configs import generate_valid_port_number

runner = CliRunner()


@given(generate_valid_ip(), generate_valid_port_number())
def test_start_remote(remote_host, remote_port) -> None:
    with patch(
        "wedge_cli.commands.start.start_agent", return_value=0
    ) as mock_start_agent:
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
    with patch(
        "wedge_cli.commands.start.start_agent", return_value=0
    ) as mock_start_agent:
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
        patch("os.environ.copy", return_value=dict()),
        patch("shutil.which", return_value=Commands.EVP_AGENT.value),
        patch("wedge_cli.commands.start.get_random_identifier", return_value="123"),
    ):
        rc = start_agent(
            connection_info=RemoteConnectionInfo(host=None, port=None),
            libraries=Libraries(libraries=[]),
        )
        command = [Commands.EVP_AGENT.value]

        env = dict()
        env[EVPEnvVars.EVP_IOT_PLATFORM] = agent_config.evp.iot_platform
        env[EVPEnvVars.EVP_MQTT_HOST] = agent_config.mqtt.host.ip_value
        env[EVPEnvVars.EVP_MQTT_PORT] = str(agent_config.mqtt.port)
        env[EVPEnvVars.EVP_DATA_DIR] = str(config_paths.evp_data_path)  # type:ignore
        env[EVPEnvVars.EVP_HTTPS_CA_CERT] = str(
            config_paths.https_ca_path
        )  # type:ignore
        env[EVPEnvVars.EVP_REPORT_STATUS_INTERVAL_MAX_SEC] = "3"
        device_id = agent_config.mqtt.device_id
        env[EVPEnvVars.EVP_MQTT_CLIENTID] = device_id if device_id else "agent-123"

        assert rc == 0
        mock_run_agent.assert_called_once_with(command, env=env, check=True)
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
        patch("os.environ.copy", return_value=dict()),
        patch("shutil.which", return_value=Commands.EVP_AGENT.value),
        patch("wedge_cli.commands.start.get_random_identifier", return_value="123"),
    ):
        rc = start_agent(
            connection_info=RemoteConnectionInfo(host=None, port=None),
            libraries=Libraries(libraries=[]),
        )
        command = [Commands.EVP_AGENT.value]

        env = dict()
        env[EVPEnvVars.EVP_IOT_PLATFORM] = agent_config.evp.iot_platform
        env[EVPEnvVars.EVP_MQTT_HOST] = agent_config.mqtt.host.ip_value
        env[EVPEnvVars.EVP_MQTT_PORT] = str(agent_config.mqtt.port)
        env[EVPEnvVars.EVP_DATA_DIR] = str(config_paths.evp_data_path)  # type:ignore
        env[EVPEnvVars.EVP_HTTPS_CA_CERT] = str(
            config_paths.https_ca_path
        )  # type:ignore
        env[EVPEnvVars.EVP_REPORT_STATUS_INTERVAL_MAX_SEC] = "3"
        device_id = agent_config.mqtt.device_id
        env[EVPEnvVars.EVP_MQTT_CLIENTID] = device_id if device_id else "agent-123"

        assert rc == 1
        mock_get_config.assert_called_once()
        assert mock_run_agent.call_count == 1
        assert mock_run_agent.call_args.args == (command,)
        assert mock_run_agent.call_args.kwargs == dict(env=env, check=True)


class MockTemporaryDirectory:
    def __init__(self, given_path):
        self.given_path = given_path

    def __enter__(self):
        return self.given_path

    def __call__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


@given(generate_agent_config(), generate_tls_config(), st.uuids())
def test_start_agent_with_tls(
    agent_config: AgentConfiguration, tls_config: TLSConfiguration, random_name: UUID
) -> None:
    with (
        patch("wedge_cli.commands.start.run") as mock_run_agent,
        patch(
            "wedge_cli.commands.start.get_config", return_value=agent_config
        ) as mock_get_config,
        patch("os.environ.copy", return_value=dict()),
        patch("shutil.which", return_value=Commands.EVP_AGENT.value),
        patch("ctypes.cdll.LoadLibrary"),
        patch(
            "wedge_cli.commands.start.TemporaryDirectory",
            new=MockTemporaryDirectory(f"/tmp/{random_name}"),
        ),
        patch("pathlib.Path.open"),
        patch("wedge_cli.commands.start.is_localhost", return_value=True),
        patch(
            "wedge_cli.commands.start.ensure_tls_setup", return_value="brokerhost"
        ) as mock_ensure_tls,
        patch("wedge_cli.commands.start.is_localhost", return_value=True),
        patch("wedge_cli.commands.start.ensure_certificate_pair_exists"),
    ):
        agent_config.tls = tls_config

        rc = start_agent(
            connection_info=RemoteConnectionInfo(host=None, port=None),
            libraries=Libraries(libraries=[]),
        )
        command = [Commands.EVP_AGENT.value]

        env = dict()
        env[EVPEnvVars.EVP_IOT_PLATFORM] = agent_config.evp.iot_platform
        env[EVPEnvVars.EVP_MQTT_HOST] = agent_config.mqtt.host.ip_value
        env[EVPEnvVars.EVP_MQTT_PORT] = str(agent_config.mqtt.port)
        env[EVPEnvVars.EVP_DATA_DIR] = str(config_paths.evp_data_path)  # type:ignore
        env[EVPEnvVars.EVP_HTTPS_CA_CERT] = str(
            config_paths.https_ca_path
        )  # type:ignore
        env[EVPEnvVars.EVP_REPORT_STATUS_INTERVAL_MAX_SEC] = "3"
        env[EVPEnvVars.EVP_MQTT_TLS_CLIENT_CERT] = str(
            config_paths.tls_cert_root / "agent.crt.pem"
        )
        env[EVPEnvVars.EVP_MQTT_TLS_CLIENT_KEY] = str(
            config_paths.tls_cert_root / "agent.key.pem"
        )
        env[EVPEnvVars.EVP_MQTT_TLS_CA_CERT] = str(agent_config.tls.ca_certificate)
        env["LD_PRELOAD"] = "libnss_wrapper.so"
        env["NSS_WRAPPER_HOSTS"] = f"/tmp/{random_name}/hosts"
        env[EVPEnvVars.EVP_MQTT_HOST] = "brokerhost"

        assert rc == 0
        mock_get_config.assert_called_once()
        mock_ensure_tls.assert_called_once()
        mock_run_agent.assert_called_once_with(command, env=env, check=True)


@given(generate_valid_ip(), generate_valid_port_number())
def test_start_agent_remote(valid_ip: str, port: int) -> None:
    with (
        patch("wedge_cli.commands.start.Listener") as mock_listener,
        patch("wedge_cli.commands.start.run") as mock_run_agent,
        patch("wedge_cli.commands.start.get_config") as mock_get_config,
        patch("wedge_cli.commands.start.is_localhost", return_value=False),
        patch("wedge_cli.commands.start.get_agent_environment") as mock_get_env,
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
        mock_get_env.assert_called_once()


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
        patch("os.environ.copy", return_value=dict()),
        patch("shutil.which", return_value=Commands.EVP_AGENT.value),
        patch("wedge_cli.commands.start.get_random_identifier", return_value="123"),
    ):
        rc = start_agent(
            connection_info=RemoteConnectionInfo(host=None, port=None),
            libraries=Libraries(libraries=libraries_list),
        )
        command = [Commands.EVP_AGENT.value]
        for library in libraries_list:
            command.append("-l")
            command.append(library)

        env = dict()
        env[EVPEnvVars.EVP_IOT_PLATFORM] = agent_config.evp.iot_platform
        env[EVPEnvVars.EVP_MQTT_HOST] = agent_config.mqtt.host.ip_value
        env[EVPEnvVars.EVP_MQTT_PORT] = str(agent_config.mqtt.port)
        env[EVPEnvVars.EVP_DATA_DIR] = str(config_paths.evp_data_path)  # type:ignore
        env[EVPEnvVars.EVP_HTTPS_CA_CERT] = str(
            config_paths.https_ca_path
        )  # type:ignore
        env[EVPEnvVars.EVP_REPORT_STATUS_INTERVAL_MAX_SEC] = "3"
        device_id = agent_config.mqtt.device_id
        env[EVPEnvVars.EVP_MQTT_CLIENTID] = device_id if device_id else "agent-123"

        assert rc == 0
        mock_run_agent.assert_called_with(command, env=env, check=True)
        mock_get_config.assert_called_once()
