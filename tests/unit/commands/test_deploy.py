import json
from unittest.mock import patch

import hypothesis.strategies as st
import pytest
from hypothesis import given
from typer.testing import CliRunner
from wedge_cli.commands.deploy import app
from wedge_cli.commands.deploy import deploy_empty
from wedge_cli.commands.deploy import deploy_manifest
from wedge_cli.utils.config import get_empty_deployment
from wedge_cli.utils.enums import Target
from wedge_cli.utils.schemas import DeploymentManifest

from tests.strategies.deployment import deployment_manifest_strategy

runner = CliRunner()


@given(st.booleans())
def test_deploy_empty_command(empty: bool) -> None:
    with (
        patch("wedge_cli.commands.deploy.Agent") as mock_agent_client,
        patch("wedge_cli.commands.deploy.deploy_empty") as mock_deploy_empty,
    ):
        if empty:
            result = runner.invoke(app, ["-e"])
            mock_agent_client.assert_called_once()
            mock_deploy_empty.assert_called_once_with(agent=mock_agent_client())
            assert result.exit_code == 0
        else:
            pass


@given(deployment_manifest_strategy(), st.sampled_from(Target))
def test_deploy_command_target(
    deployment_manifest: DeploymentManifest, target: Target
) -> None:
    with (
        patch("wedge_cli.commands.deploy.Agent") as mock_agent_client,
        patch("wedge_cli.commands.deploy.deploy_manifest") as mock_deploy_manifest,
        patch(
            "wedge_cli.commands.deploy.get_deployment_schema",
            return_value=deployment_manifest,
        ) as mock_get_deployment,
    ):
        result = runner.invoke(app, [target.value])
        mock_get_deployment.assert_called_once()
        mock_agent_client.assert_called_once()
        mock_deploy_manifest.assert_called_once_with(
            agent=mock_agent_client(),
            deployment_manifest=deployment_manifest,
            signed=False,
            timeout=10,
            target=target,
        )
        assert result.exit_code == 0


@given(deployment_manifest_strategy())
def test_deploy_command_signed(deployment_manifest: DeploymentManifest) -> None:
    with (
        patch("wedge_cli.commands.deploy.Agent") as mock_agent_client,
        patch("wedge_cli.commands.deploy.deploy_manifest") as mock_deploy_manifest,
        patch(
            "wedge_cli.commands.deploy.get_deployment_schema",
            return_value=deployment_manifest,
        ) as mock_get_deployment,
    ):
        result = runner.invoke(app, ["-s"])
        mock_get_deployment.assert_called_once()
        mock_agent_client.assert_called_once()
        mock_deploy_manifest.assert_called_once_with(
            agent=mock_agent_client(),
            deployment_manifest=deployment_manifest,
            signed=True,
            timeout=10,
            target=None,
        )
        assert result.exit_code == 0


@given(deployment_manifest_strategy(), st.integers())
def test_deploy_command_timeout(
    deployment_manifest: DeploymentManifest, timeout: int
) -> None:
    with (
        patch("wedge_cli.commands.deploy.Agent") as mock_agent_client,
        patch("wedge_cli.commands.deploy.deploy_manifest") as mock_deploy_manifest,
        patch(
            "wedge_cli.commands.deploy.get_deployment_schema",
            return_value=deployment_manifest,
        ) as mock_get_deployment,
    ):
        result = runner.invoke(app, ["-t", timeout])
        mock_get_deployment.assert_called_once()
        mock_agent_client.assert_called_once()
        mock_deploy_manifest.assert_called_once_with(
            agent=mock_agent_client(),
            deployment_manifest=deployment_manifest,
            signed=False,
            timeout=timeout,
            target=None,
        )
        assert result.exit_code == 0


def test_deploy_empty():
    empty_deploy = get_empty_deployment()
    with (
        patch("wedge_cli.commands.deploy.Agent") as mock_agent_client,
        patch(
            "wedge_cli.commands.deploy.get_empty_deployment", return_value=empty_deploy
        ) as mock_get_empty_deployment,
    ):
        deploy_empty(mock_agent_client())
        mock_get_empty_deployment.assert_called_once()
        mock_agent_client.return_value.deploy.assert_called_once_with(
            deployment=empty_deploy
        )


@given(
    deployment_manifest_strategy(),
    st.booleans(),
    st.integers(),
    st.sampled_from(Target),
)
def test_deploy_manifest(
    deployment_manifest: DeploymentManifest, signed: bool, timeout: int, target: Target
):
    with (
        patch("wedge_cli.commands.deploy.Agent") as mock_agent_client,
        patch("wedge_cli.commands.deploy._WebServer") as mock_webserver,
        patch("wedge_cli.commands.deploy.Path") as mock_path,
    ):
        mock_path.exists.return_value = True
        deploy_manifest(
            mock_agent_client(), deployment_manifest, signed, timeout, target
        )
        mock_path.assert_called_once_with("bin")
        mock_webserver.assert_called_once_with(mock_agent_client())
        mock_webserver.return_value.update_deployment_manifest.assert_called_once_with(
            deployment_manifest, target, signed
        )
        num_modules = len(deployment_manifest.deployment.modules.keys())
        mock_webserver.return_value.start.assert_called_once_with(num_modules, timeout)
        mock_agent_client.return_value.deploy.assert_called_once_with(
            json.dumps(deployment_manifest.model_dump())
        )
        mock_webserver.return_value.close.assert_called_once()


@given(
    deployment_manifest_strategy(),
    st.booleans(),
    st.integers(),
    st.sampled_from(Target),
)
def test_deploy_manifest_no_bin(
    deployment_manifest: DeploymentManifest, signed: bool, timeout: int, target: Target
):
    with (
        patch(
            "wedge_cli.commands.deploy.Path.exists", return_value=False
        ) as mock_exists,
        patch("wedge_cli.commands.deploy.Agent") as mock_agent_client,
    ):
        with pytest.raises(SystemExit):
            deploy_manifest(
                mock_agent_client(), deployment_manifest, signed, timeout, target
            )
        mock_exists.assert_called_once()
