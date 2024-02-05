from unittest.mock import patch

from hypothesis import given
from hypothesis import strategies as st
from typer.testing import CliRunner
from wedge_cli.commands.rpc import app

runner = CliRunner()


@given(
    st.text(min_size=1, max_size=5),
    st.text(min_size=1, max_size=5),
    st.text(min_size=1, max_size=5),
)
def test_rpc_command(instance_id: str, method: str, params: str):
    with (
        patch("wedge_cli.commands.rpc.Agent"),
        patch("wedge_cli.commands.rpc.rpc_task") as mock_rpc,
    ):
        result = runner.invoke(app, [instance_id, method, params])
        mock_rpc.assert_called_with(instance_id, method, params)
        assert result.exit_code == 0


@given(
    st.text(min_size=1, max_size=5),
    st.text(min_size=1, max_size=5),
    st.text(min_size=1, max_size=5),
)
def test_rpc_command_exception(instance_id: str, method: str, params: str):
    with (
        patch("wedge_cli.commands.rpc.Agent") as mock_agent,
        patch("wedge_cli.commands.rpc.Agent.mqtt_scope") as mock_mqtt,
    ):
        mock_mqtt.side_effect = ConnectionError
        result = runner.invoke(app, [instance_id, method, params])
        mock_agent.assert_called()
        assert result.exit_code == 1
