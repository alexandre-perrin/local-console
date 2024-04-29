from unittest.mock import patch

from hypothesis import given
from local_console.commands.get import app
from local_console.commands.get import on_message_print_payload
from local_console.commands.get import on_message_telemetry
from local_console.core.camera import MQTTTopics
from local_console.core.enums import GetObjects
from typer.testing import CliRunner

from tests.strategies.configs import generate_text

runner = CliRunner()


def test_get_deployment_command():
    with (patch("local_console.commands.get.Agent") as mock_agent,):
        result = runner.invoke(app, [GetObjects.DEPLOYMENT.value])
        mock_agent.return_value.read_only_loop.assert_called_once_with(
            subs_topics=[MQTTTopics.ATTRIBUTES.value],
            message_task=on_message_print_payload,
        )
        assert result.exit_code == 0


def test_get_telemetry_command():
    with (patch("local_console.commands.get.Agent") as mock_agent,):
        result = runner.invoke(app, [GetObjects.TELEMETRY.value])
        mock_agent.return_value.read_only_loop.assert_called_once_with(
            subs_topics=[MQTTTopics.TELEMETRY.value],
            message_task=on_message_telemetry,
        )
        assert result.exit_code == 0


@given(generate_text())
def test_get_instance_command(instance_id: str):
    with (
        patch("local_console.commands.get.Agent") as mock_agent,
        patch("local_console.commands.get.on_message_instance") as mock_msg_inst,
    ):
        result = runner.invoke(app, [GetObjects.INSTANCE.value, instance_id])
        mock_agent.return_value.read_only_loop.assert_called_once_with(
            subs_topics=[MQTTTopics.ATTRIBUTES.value],
            message_task=mock_msg_inst.return_value,
        )
        assert result.exit_code == 0
        mock_msg_inst.assert_called_once_with(instance_id)
