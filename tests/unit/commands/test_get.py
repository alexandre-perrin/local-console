from unittest.mock import patch

from hypothesis import given
from hypothesis import strategies as st
from typer.testing import CliRunner
from wedge_cli.commands.get import app
from wedge_cli.utils.enums import GetObjects

runner = CliRunner()


def test_get_deployment_command():
    with (patch("wedge_cli.commands.get.Agent") as mock_agent,):
        result = runner.invoke(app, [GetObjects.DEPLOYMENT.value])
        mock_agent.return_value.get_deployment.assert_called_once()
        assert result.exit_code == 0


def test_get_telemetry_command():
    with (patch("wedge_cli.commands.get.Agent") as mock_agent,):
        result = runner.invoke(app, [GetObjects.TELEMETRY.value])
        mock_agent.return_value.get_telemetry.assert_called_once()
        assert result.exit_code == 0


@given(st.text(min_size=1, max_size=5))
def test_get_instance_command(instance_id: str):
    with (patch("wedge_cli.commands.get.Agent") as mock_agent,):
        result = runner.invoke(app, [GetObjects.INSTANCE.value, instance_id])
        mock_agent.return_value.get_instance.assert_called_once_with(instance_id)
        assert result.exit_code == 0
