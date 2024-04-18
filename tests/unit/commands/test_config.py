from configparser import ConfigParser
from unittest.mock import AsyncMock
from unittest.mock import patch

from hypothesis import given
from hypothesis import strategies as st
from typer.testing import CliRunner
from wedge_cli.commands.config import app
from wedge_cli.core.enums import config_paths
from wedge_cli.core.enums import GetCommands
from wedge_cli.core.schemas.schemas import AgentConfiguration
from wedge_cli.core.schemas.schemas import DesiredDeviceConfig
from wedge_cli.core.schemas.schemas import IPAddress
from wedge_cli.core.schemas.schemas import OnWireProtocol
from wedge_cli.core.schemas.schemas import RemoteConnectionInfo

from tests.strategies.configs import generate_agent_config
from tests.strategies.configs import generate_identifiers
from tests.strategies.configs import generate_invalid_ip
from tests.strategies.configs import generate_text
from tests.strategies.configs import generate_valid_ip
from tests.strategies.configs import generate_valid_port_number
from tests.strategies.path import path_strategy

runner = CliRunner()


@given(generate_text(), generate_agent_config())
def test_config_get_command(parser_return: str, agent_config: AgentConfiguration):
    with (
        patch(
            "wedge_cli.commands.config.get_config", return_value=agent_config
        ) as mock_get_config,
        patch(
            "wedge_cli.commands.config.parse_section_to_ini", return_value=parser_return
        ) as mock_parse_to_ini,
        patch(
            "wedge_cli.commands.config.check_section_and_params"
        ) as mock_checks_section_and_params,
    ):
        for section_name in agent_config.model_fields.keys():
            section_value = getattr(agent_config, section_name)
            for parameter in section_value.model_fields.keys():
                result = runner.invoke(
                    app, [GetCommands.GET.value, section_name, parameter]
                )
                mock_parse_to_ini.assert_called_with(
                    section_value, section_name, parameter
                )
                mock_get_config.assert_called()
                mock_checks_section_and_params.assert_called_with(
                    agent_config, section_name, parameter
                )
                assert result.exit_code == 0


@given(generate_text(), generate_agent_config())
def test_config_get_command_section_none(
    parser_return: str, agent_config: AgentConfiguration
):
    with (
        patch(
            "wedge_cli.commands.config.get_config", return_value=agent_config
        ) as mock_get_config,
        patch(
            "wedge_cli.commands.config.parse_section_to_ini", return_value=parser_return
        ) as mock_parse_to_ini,
    ):
        result = runner.invoke(app, [GetCommands.GET.value])

        for section_name in agent_config.model_fields.keys():
            section_value = getattr(agent_config, section_name)
            mock_parse_to_ini.assert_any_call(section_value, section_name)
            mock_get_config.assert_called()
            assert result.exit_code == 0


@given(generate_agent_config())
def test_config_get_command_value_error(agent_config: AgentConfiguration):
    with (
        patch(
            "wedge_cli.commands.config.get_config", return_value=agent_config
        ) as mock_get_config,
        patch(
            "wedge_cli.commands.config.check_section_and_params", side_effect=ValueError
        ) as mock_checks_section_and_params,
    ):
        for section_name in agent_config.model_fields.keys():
            section_value = getattr(agent_config, section_name)
            for parameter in section_value.model_fields.keys():
                result = runner.invoke(
                    app, [GetCommands.GET.value, section_name, parameter]
                )
                mock_get_config.assert_called()
                mock_checks_section_and_params.assert_called()
                assert result.exit_code == 1


@given(generate_valid_ip(), generate_agent_config())
def test_config_set_command(new_value: str, agent_config: AgentConfiguration):
    with (
        patch(
            "wedge_cli.commands.config.get_config", return_value=agent_config
        ) as mock_get_config,
        patch("wedge_cli.commands.config.schema_to_parser") as mock_schema_to_parser,
        patch(
            "wedge_cli.commands.config.check_section_and_params"
        ) as mock_checks_section_and_params,
        patch("builtins.open") as mock_open,
    ):
        for section_name in agent_config.model_fields.keys():
            section_value = getattr(agent_config, section_name)
            if "host" in section_value.model_fields.keys():
                config_dict = agent_config.model_dump()
                config_dict[section_name]["host"] = new_value

                config_parser = ConfigParser()
                for section_names, values in config_dict.items():
                    if "host" in values.keys():
                        if isinstance(values["host"], dict):
                            values["host"] = values["host"]["ip_value"]
                    # Replace null values with empty strings, for the config_parser
                    values = {key: val if val else "" for key, val in values.items()}
                    config_parser[section_names] = values
                mock_schema_to_parser.return_value = config_parser

                result = runner.invoke(
                    app, [GetCommands.SET.value, section_name, "host", new_value]
                )
                mock_get_config.assert_called()
                mock_schema_to_parser.assert_called_with(
                    agent_config, section_name, "host", new_value
                )
                mock_open.assert_called_with(config_paths.config_path, "w")
                mock_checks_section_and_params.assert_called()
                assert result.exit_code == 0


@given(
    generate_text(),
    generate_text(),
    generate_agent_config(),
)
def test_config_set_command_value_error(
    section_miss: str, new_value: str, agent_config: AgentConfiguration
):
    with (
        patch(
            "wedge_cli.commands.config.get_config", return_value=agent_config
        ) as mock_get_config,
        patch(
            "wedge_cli.commands.config.check_section_and_params", side_effect=ValueError
        ) as mock_checks_section_and_params,
    ):
        for section_name in agent_config.model_fields.keys():
            section_value = getattr(agent_config, section_name)
            for parameter in section_value.model_fields.keys():
                result = runner.invoke(
                    app, [GetCommands.SET.value, section_miss, parameter, new_value]
                )
                mock_get_config.assert_called()
                mock_checks_section_and_params.assert_called()
                assert result.exit_code == 1


@given(
    generate_agent_config(),
)
def test_config_unset_nullable_parameter(agent_config: AgentConfiguration):
    with (
        patch(
            "wedge_cli.commands.config.get_config", return_value=agent_config
        ) as mock_get_config,
        patch("pathlib.Path.open") as mock_open,
    ):
        result = runner.invoke(app, [GetCommands.UNSET.value, "mqtt", "device_id"])
        assert result.exit_code == 0
        mock_get_config.assert_called()
        mock_open.assert_called_with("w")


@given(
    generate_agent_config(),
)
def test_config_unset_not_nullable_error(agent_config: AgentConfiguration):
    with (
        patch(
            "wedge_cli.commands.config.get_config", return_value=agent_config
        ) as mock_get_config,
    ):
        result = runner.invoke(
            app,
            [
                GetCommands.UNSET.value,
                "mqtt",
                "host",
            ],  # "mqtt.host" is not a nullable parameter
        )
        assert result.exit_code == 1
        assert type(result.exception) is SystemExit
        assert result.exception.args[0].startswith("Error unsetting config param")
        mock_get_config.assert_called()


@given(
    path_strategy(),
    generate_valid_ip(),
    generate_valid_port_number(),
    generate_agent_config(),
)
def test_config_send_command(
    config_filepath: str, ip: str, port: int, agent_config: AgentConfiguration
):
    with (
        patch(
            "wedge_cli.commands.config.get_config", return_value=agent_config
        ) as mock_get_config,
        patch("wedge_cli.commands.config.send_config") as mock_send_config,
    ):
        result = runner.invoke(
            app,
            [
                GetCommands.SEND.value,
                "--config-file",
                str(config_filepath) + ".ini",
                "--ip",
                ip,
                "--port",
                port,
            ],
        )
        mock_get_config.assert_called()
        mock_send_config.assert_called_with(
            agent_config.model_dump(),
            RemoteConnectionInfo(host=IPAddress(ip_value=ip), port=port),
        )
        assert result.exit_code == 0


@given(
    path_strategy(),
    generate_valid_ip(),
    generate_valid_port_number(),
)
def test_config_send_command_no_ini(config_filepath: str, ip: str, port: int):
    result = runner.invoke(
        app,
        [
            GetCommands.SEND.value,
            "--config-file",
            str(config_filepath),
            "--ip",
            ip,
            "--port",
            port,
        ],
    )
    assert result.exit_code == 1


@given(path_strategy(), generate_invalid_ip(), generate_valid_port_number())
def test_config_send_command_invalid_ip(
    config_filepath: str, invalid_ip: str, port: int
):
    result = runner.invoke(
        app,
        [
            GetCommands.SEND.value,
            "--config-file",
            str(config_filepath) + ".ini",
            "--ip",
            invalid_ip,
            "--port",
            port,
        ],
    )
    assert result.exit_code == 1


@given(
    generate_identifiers(max_size=5),
    generate_identifiers(max_size=5),
    generate_identifiers(max_size=5),
)
def test_config_instance_command(instance_id: str, method: str, params: str):
    with (
        patch("wedge_cli.commands.config.Agent"),
        patch("wedge_cli.commands.config.configure_task") as mock_configure,
    ):
        result = runner.invoke(app, ["instance", instance_id, method, params])
        mock_configure.assert_called_with(instance_id, method, params)
        assert result.exit_code == 0


@given(
    generate_identifiers(max_size=5),
    generate_identifiers(max_size=5),
    generate_identifiers(max_size=5),
)
def test_config_instance_command_exception(instance_id: str, method: str, params: str):
    with (
        patch("wedge_cli.commands.config.Agent") as mock_agent,
        patch("wedge_cli.commands.config.Agent.mqtt_scope") as mock_mqtt,
    ):
        mock_mqtt.side_effect = ConnectionError
        result = runner.invoke(app, ["instance", instance_id, method, params])
        mock_agent.assert_called()
        assert result.exit_code == 1


@given(st.integers(min_value=0, max_value=300), st.integers(min_value=0, max_value=300))
def test_config_device_command(interval_max: int, interval_min: int):
    with (
        patch("wedge_cli.commands.config.Agent") as mock_agent,
        # patch("wedge_cli.commands.config.Agent.determine_onwire_schema", return_value=),
        patch(
            "wedge_cli.commands.config.config_device_task", return_value=0
        ) as mock_configure,
    ):
        mock_agent.determine_onwire_schema = AsyncMock(return_value=OnWireProtocol.EVP2)
        result = runner.invoke(app, ["device", f"{interval_max}", f"{interval_min}"])
        desired_device_config = DesiredDeviceConfig(
            reportStatusIntervalMax=interval_max, reportStatusIntervalMin=interval_min
        )
        mock_configure.assert_awaited_with(desired_device_config)
        assert result.exit_code == 0


@given(
    st.integers(min_value=-100, max_value=-1), st.integers(min_value=-100, max_value=-1)
)
def test_config_device_command_invalid_range(interval_max: int, interval_min: int):
    with (patch("wedge_cli.commands.config.config_device_task") as mock_configure,):
        result = runner.invoke(app, ["device", interval_max, interval_min])
        mock_configure.assert_not_awaited()
        assert result.exit_code == 1
