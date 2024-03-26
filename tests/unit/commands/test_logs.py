from unittest.mock import patch

from hypothesis import given
from hypothesis import strategies as st
from typer.testing import CliRunner
from wedge_cli.commands.logs import app
from wedge_cli.core.camera import MQTTTopics
from wedge_cli.core.schemas import OnWireProtocol

from tests.strategies.configs import generate_text

runner = CliRunner()


@given(
    generate_text(),
    st.integers(),
    st.sampled_from(OnWireProtocol),
)
def test_logs_command(
    instance_id: str,
    timeout: int,
    onwire_schema: OnWireProtocol,
):
    with (
        patch("wedge_cli.commands.logs.Agent") as mock_agent_client,
        patch(
            "wedge_cli.clients.agent.OnWireProtocol.from_iot_spec",
            return_value=onwire_schema,
        ),
        patch("trio.run") as mock_run,
        patch("wedge_cli.commands.logs.on_message_logs") as mock_msg_logs,
    ):
        result = runner.invoke(app, ["--timeout", timeout, instance_id])
        mock_run.assert_called_with(
            mock_agent_client.return_value.request_instance_logs, instance_id
        )
        mock_agent_client.return_value.read_only_loop.assert_called_once_with(
            subs_topics=[MQTTTopics.TELEMETRY.value],
            message_task=mock_msg_logs.return_value,
        )
        assert result.exit_code == 0
        mock_msg_logs.assert_called_once_with(instance_id, timeout)


@given(
    generate_text(),
    st.integers(),
)
def test_logs_command_exception(instance_id: str, timeout: int):
    with (
        patch("wedge_cli.commands.logs.Agent") as mock_agent_client,
        patch("trio.run") as mock_run,
    ):
        mock_agent_client.return_value.read_only_loop.side_effect = ConnectionError
        result = runner.invoke(app, ["--timeout", timeout, instance_id])
        mock_agent_client.assert_called()
        mock_run.assert_called_once()
        assert result.exit_code == 1
