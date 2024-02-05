from unittest.mock import patch

from hypothesis import given
from hypothesis import strategies as st
from typer.testing import CliRunner
from wedge_cli.commands.logs import app

runner = CliRunner()


@given(
    st.text(min_size=1, max_size=5),
    st.integers(),
)
def test_logs_command(instance_id: str, timeout: int):
    with (
        patch("wedge_cli.commands.logs.Agent") as mock_agent_client,
        patch("trio.run") as mock_run,
    ):
        result = runner.invoke(app, ["--timeout", timeout, instance_id])
        mock_run.assert_called_with(
            mock_agent_client.return_value.request_instance_logs, instance_id
        )
        mock_agent_client.return_value.get_instance_logs.assert_called_once_with(
            instance_id, timeout
        )
        assert result.exit_code == 0


@given(
    st.text(min_size=1, max_size=5),
    st.integers(),
)
def test_logs_command_exception(instance_id: str, timeout: int):
    with (
        patch("wedge_cli.commands.logs.Agent") as mock_agent_client,
        patch("trio.run") as mock_run,
    ):
        mock_agent_client.return_value.get_instance_logs.side_effect = ConnectionError
        result = runner.invoke(app, ["--timeout", timeout, instance_id])
        mock_agent_client.assert_called()
        mock_run.assert_called_once()
        assert result.exit_code == 1
