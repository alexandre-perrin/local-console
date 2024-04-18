from unittest.mock import patch

from hypothesis import given
from typer.testing import CliRunner
from wedge_cli.commands.rpc import app
from wedge_cli.core.schemas.schemas import AgentConfiguration

from tests.strategies.configs import generate_agent_config
from tests.strategies.configs import generate_text

runner = CliRunner()


@given(
    generate_text(),
    generate_text(),
    generate_text(),
    generate_agent_config(),
)
def test_rpc_command(
    instance_id: str, method: str, params: str, agent_config: AgentConfiguration
):
    with (
        patch("wedge_cli.commands.rpc.Agent"),
        patch("wedge_cli.commands.rpc.rpc_task") as mock_rpc,
        patch("wedge_cli.commands.rpc.Agent.get_config", return_value=agent_config),
    ):
        result = runner.invoke(app, [instance_id, method, params])
        mock_rpc.assert_called_with(instance_id, method, params)
        assert result.exit_code == 0


@given(
    generate_text(),
    generate_text(),
    generate_text(),
    generate_agent_config(),
)
def test_rpc_command_exception(
    instance_id: str, method: str, params: str, agent_config: AgentConfiguration
):
    with (
        patch("wedge_cli.commands.rpc.Agent") as mock_agent,
        patch("wedge_cli.commands.rpc.Agent.mqtt_scope") as mock_mqtt,
        patch("wedge_cli.commands.rpc.Agent.get_config", return_value=agent_config),
    ):
        mock_mqtt.side_effect = ConnectionError
        result = runner.invoke(app, [instance_id, method, params])
        mock_agent.assert_called()
        assert result.exit_code == 1
