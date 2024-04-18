from datetime import timedelta
from unittest.mock import ANY
from unittest.mock import AsyncMock
from unittest.mock import patch

import hypothesis.strategies as st
import pytest
from hypothesis import given
from hypothesis import settings
from typer.testing import CliRunner
from wedge_cli.clients.agent import Agent
from wedge_cli.clients.agent import check_attributes_request
from wedge_cli.commands.deploy import app
from wedge_cli.core.camera import MQTTTopics
from wedge_cli.core.commands.deploy import get_empty_deployment
from wedge_cli.core.enums import Target
from wedge_cli.core.schemas.schemas import AgentConfiguration
from wedge_cli.core.schemas.schemas import DeploymentManifest
from wedge_cli.core.schemas.schemas import OnWireProtocol

from tests.strategies.configs import generate_agent_config
from tests.strategies.deployment import deployment_manifest_strategy

runner = CliRunner()


def test_get_empty_deployment():
    empty = get_empty_deployment()
    assert len(empty.deployment.modules) == 0
    assert len(empty.deployment.instanceSpecs) == 0
    assert len(empty.deployment.deploymentId) != 0


@given(generate_agent_config())
def test_deploy_empty_command(agent_config: AgentConfiguration) -> None:
    with (
        patch("wedge_cli.commands.deploy.Agent") as mock_agent_client,
        patch("wedge_cli.commands.deploy.get_empty_deployment") as mock_get_deployment,
        patch("wedge_cli.commands.deploy.get_config", return_value=agent_config),
        patch("wedge_cli.commands.deploy.is_localhost", return_value=True),
        patch("wedge_cli.commands.deploy.exec_deployment") as mock_exec_deploy,
    ):
        result = runner.invoke(app, ["-e"])
        mock_agent_client.assert_called_once()
        mock_get_deployment.assert_called_once()
        mock_exec_deploy.assert_called_once_with(
            mock_agent_client(), mock_get_deployment.return_value, ANY, ANY, ANY, ANY
        )
        assert result.exit_code == 0


@given(deployment_manifest_strategy(), st.sampled_from(Target), generate_agent_config())
def test_deploy_command_target(
    deployment_manifest: DeploymentManifest,
    target: Target,
    agent_config: AgentConfiguration,
) -> None:
    with (
        patch("wedge_cli.commands.deploy.Agent") as mock_agent_client,
        patch("wedge_cli.commands.deploy.get_config", return_value=agent_config),
        patch("wedge_cli.commands.deploy.is_localhost", return_value=True),
        patch("wedge_cli.commands.deploy.exec_deployment") as mock_exec_deploy,
        patch(
            "wedge_cli.commands.deploy.update_deployment_manifest"
        ) as mock_update_manifest,
        patch(
            "wedge_cli.commands.deploy.make_unique_module_ids"
        ) as mock_make_unique_ids,
        patch(
            "wedge_cli.commands.deploy.get_deployment_schema",
            return_value=deployment_manifest,
        ) as mock_get_deployment,
        patch("pathlib.Path.is_dir") as mock_check_dir,
    ):
        result = runner.invoke(app, [target.value])
        mock_agent_client.assert_called_once()
        mock_check_dir.assert_called_once()
        mock_get_deployment.assert_called_once()
        mock_update_manifest.assert_called_once_with(
            deployment_manifest,
            ANY,
            ANY,
            ANY,
            target,
            False,
        )
        mock_make_unique_ids.assert_called_once()
        mock_exec_deploy.assert_called_once_with(
            mock_agent_client(), deployment_manifest, ANY, ANY, ANY, ANY
        )
        assert result.exit_code == 0


@settings(deadline=timedelta(seconds=10))
@given(deployment_manifest_strategy(), generate_agent_config())
def test_deploy_command_signed(
    deployment_manifest: DeploymentManifest, agent_config: AgentConfiguration
) -> None:
    with (
        patch("wedge_cli.commands.deploy.Agent") as mock_agent_client,
        patch("wedge_cli.commands.deploy.get_config", return_value=agent_config),
        patch("wedge_cli.commands.deploy.is_localhost", return_value=True),
        patch("wedge_cli.commands.deploy.exec_deployment") as mock_exec_deploy,
        patch(
            "wedge_cli.commands.deploy.update_deployment_manifest"
        ) as mock_update_manifest,
        patch(
            "wedge_cli.commands.deploy.make_unique_module_ids"
        ) as mock_make_unique_ids,
        patch(
            "wedge_cli.commands.deploy.get_deployment_schema",
            return_value=deployment_manifest,
        ) as mock_get_deployment,
        patch("pathlib.Path.is_dir") as mock_check_dir,
    ):
        result = runner.invoke(app, ["-s"])
        mock_agent_client.assert_called_once()
        mock_check_dir.assert_called_once()
        mock_get_deployment.assert_called_once()
        mock_update_manifest.assert_called_once_with(
            deployment_manifest,
            ANY,
            ANY,
            ANY,
            ANY,
            True,
        )
        mock_make_unique_ids.assert_called_once()
        mock_exec_deploy.assert_called_once_with(
            mock_agent_client(), deployment_manifest, ANY, ANY, ANY, ANY
        )
        assert result.exit_code == 0


@given(deployment_manifest_strategy(), generate_agent_config())
def test_deploy_command_timeout(
    deployment_manifest: DeploymentManifest,
    agent_config: AgentConfiguration,
) -> None:
    # TODO: improve timeout management
    timeout = 6
    with (
        patch("wedge_cli.commands.deploy.Agent") as mock_agent_client,
        patch("wedge_cli.commands.deploy.get_config", return_value=agent_config),
        patch("wedge_cli.commands.deploy.is_localhost", return_value=True),
        patch("wedge_cli.commands.deploy.exec_deployment") as mock_exec_deploy,
        patch(
            "wedge_cli.commands.deploy.update_deployment_manifest"
        ) as mock_update_manifest,
        patch(
            "wedge_cli.commands.deploy.make_unique_module_ids"
        ) as mock_make_unique_ids,
        patch(
            "wedge_cli.commands.deploy.get_deployment_schema",
            return_value=deployment_manifest,
        ) as mock_get_deployment,
        patch("pathlib.Path.is_dir") as mock_check_dir,
    ):
        result = runner.invoke(app, ["-t", timeout])
        mock_agent_client.assert_called_once()
        mock_check_dir.assert_called_once()
        mock_get_deployment.assert_called_once()
        mock_update_manifest.assert_called_once_with(
            deployment_manifest,
            ANY,
            ANY,
            ANY,
            None,
            False,
        )
        mock_make_unique_ids.assert_called_once()
        mock_exec_deploy.assert_called_once_with(
            mock_agent_client(), deployment_manifest, ANY, ANY, ANY, timeout
        )
        assert result.exit_code == 0


@given(
    st.booleans(),
    st.integers(),
    st.sampled_from(Target),
    generate_agent_config(),
)
def test_deploy_manifest_no_bin(
    signed: bool,
    timeout: int,
    target: Target,
    agent_config: AgentConfiguration,
):
    with (
        patch("wedge_cli.commands.deploy.is_localhost", return_value=True),
        patch("wedge_cli.commands.deploy.Agent") as mock_agent_client,
        patch("wedge_cli.commands.deploy.get_config", return_value=agent_config),
        patch(
            "wedge_cli.commands.deploy.Path.is_dir", return_value=False
        ) as mock_is_dir,
    ):
        result = runner.invoke(
            app, ["-t", timeout, *(["-s"] if signed else []), target.value]
        )
        assert result.exit_code != 0
        mock_agent_client.assert_called_once()
        mock_is_dir.assert_called_once()


@given(
    st.integers(min_value=1), generate_agent_config(), st.sampled_from(OnWireProtocol)
)
@pytest.mark.trio
async def test_attributes_request_handling(
    mqtt_req_id: int,
    agent_config: AgentConfiguration,
    onwire_schema: OnWireProtocol,
):
    with (
        patch("wedge_cli.clients.agent.get_config", return_value=agent_config),
        patch(
            "wedge_cli.clients.agent.OnWireProtocol.from_iot_spec",
            return_value=onwire_schema,
        ),
        patch("wedge_cli.clients.agent.paho.Client"),
        patch("wedge_cli.clients.agent.AsyncClient"),
    ):
        request_topic = MQTTTopics.ATTRIBUTES_REQ.value.replace("+", str(mqtt_req_id))

        agent = Agent()
        agent.publish = AsyncMock()
        async with agent.mqtt_scope([MQTTTopics.ATTRIBUTES_REQ.value]):
            check = await check_attributes_request(agent, request_topic, "{}")

        response_topic = request_topic.replace("request", "response")
        agent.publish.assert_called_once_with(response_topic, "{}")
        assert check
