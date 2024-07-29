# Copyright 2024 Sony Semiconductor Solutions Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
import json
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from unittest.mock import ANY
from unittest.mock import AsyncMock
from unittest.mock import patch

import hypothesis.strategies as st
import pytest
import trio
from hypothesis import given
from hypothesis import settings
from local_console.clients.agent import Agent
from local_console.clients.agent import check_attributes_request
from local_console.commands.deploy import app
from local_console.commands.deploy import exec_deployment
from local_console.commands.deploy import project_binary_lookup
from local_console.commands.deploy import stimulus_proc
from local_console.core.camera.enums import MQTTTopics
from local_console.core.commands.deploy import get_empty_deployment
from local_console.core.enums import Target
from local_console.core.schemas.schemas import AgentConfiguration
from local_console.core.schemas.schemas import DeploymentManifest
from local_console.core.schemas.schemas import OnWireProtocol
from typer.testing import CliRunner

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
        patch("local_console.commands.deploy.Agent") as mock_agent_client,
        patch("local_console.commands.deploy.DeployFSM") as mock_gen_deploy_fsm,
        patch(
            "local_console.commands.deploy.get_empty_deployment"
        ) as mock_get_deployment,
        patch("local_console.commands.deploy.get_config", return_value=agent_config),
        patch("local_console.commands.deploy.is_localhost", return_value=True),
        patch("local_console.commands.deploy.exec_deployment") as mock_exec_deploy,
    ):
        result = runner.invoke(app, ["-e"])
        mock_agent_client.assert_called_once()

        mock_gen_deploy_fsm.instantiate.assert_called_once()
        mock_deploy_fsm = mock_gen_deploy_fsm.instantiate.return_value

        mock_get_deployment.assert_called_once()
        mock_deploy_fsm.set_manifest.assert_called_once_with(
            mock_get_deployment.return_value
        )

        mock_exec_deploy.assert_called_once_with(
            mock_agent_client(),
            mock_deploy_fsm,
        )
        assert result.exit_code == 0


@given(deployment_manifest_strategy(), st.sampled_from(Target), generate_agent_config())
def test_deploy_command_target(
    deployment_manifest: DeploymentManifest,
    target: Target,
    agent_config: AgentConfiguration,
) -> None:
    with (
        patch("local_console.commands.deploy.Agent") as mock_agent_client,
        patch("local_console.commands.deploy.get_config", return_value=agent_config),
        patch("local_console.commands.deploy.is_localhost", return_value=True),
        patch("local_console.commands.deploy.DeployFSM") as mock_gen_deploy_fsm,
        patch("local_console.commands.deploy.exec_deployment") as mock_exec_deploy,
        patch(
            "local_console.commands.deploy.module_deployment_setup",
            return_value=deployment_manifest,
        ) as mock_setup_manifest,
        patch(
            "local_console.commands.deploy.project_binary_lookup",
        ) as mock_get_path,
        patch("pathlib.Path.is_dir") as mock_check_dir,
    ):
        result = runner.invoke(app, [target.value])
        mock_agent_client.assert_called_once()
        mock_check_dir.assert_called_once()

        mock_gen_deploy_fsm.instantiate.assert_called_once()
        mock_deploy_fsm = mock_gen_deploy_fsm.instantiate.return_value

        mock_get_path.assert_called_once_with(
            ANY,
            ANY,
            target,
            False,
        )
        mock_setup_manifest.assert_called_once_with(
            ANY,
            mock_get_path.return_value,
            mock_deploy_fsm.webserver,
            ANY,
            ANY,
        )

        mock_deploy_fsm.set_manifest.assert_called_once_with(deployment_manifest)
        mock_exec_deploy.assert_called_once_with(
            mock_agent_client(),
            mock_deploy_fsm,
        )
        assert result.exit_code == 0


@settings(deadline=timedelta(seconds=10))
@given(deployment_manifest_strategy(), generate_agent_config())
def test_deploy_command_signed(
    deployment_manifest: DeploymentManifest, agent_config: AgentConfiguration
) -> None:
    with (
        patch("local_console.commands.deploy.Agent") as mock_agent_client,
        patch("local_console.commands.deploy.get_config", return_value=agent_config),
        patch("local_console.commands.deploy.is_localhost", return_value=True),
        patch("local_console.commands.deploy.DeployFSM") as mock_gen_deploy_fsm,
        patch("local_console.commands.deploy.exec_deployment") as mock_exec_deploy,
        patch(
            "local_console.commands.deploy.module_deployment_setup",
            return_value=deployment_manifest,
        ) as mock_setup_manifest,
        patch(
            "local_console.commands.deploy.project_binary_lookup",
        ) as mock_get_path,
        patch("pathlib.Path.is_dir") as mock_check_dir,
    ):
        result = runner.invoke(app, ["-s"])
        mock_agent_client.assert_called_once()
        mock_check_dir.assert_called_once()

        mock_gen_deploy_fsm.instantiate.assert_called_once()
        mock_deploy_fsm = mock_gen_deploy_fsm.instantiate.return_value

        mock_get_path.assert_called_once_with(
            ANY,
            ANY,
            ANY,
            True,
        )
        mock_setup_manifest.assert_called_once_with(
            ANY,
            mock_get_path.return_value,
            mock_deploy_fsm.webserver,
            ANY,
            ANY,
        )

        mock_deploy_fsm.set_manifest.assert_called_once_with(deployment_manifest)
        mock_exec_deploy.assert_called_once_with(
            mock_agent_client(),
            mock_deploy_fsm,
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
        patch("local_console.commands.deploy.Agent") as mock_agent_client,
        patch("local_console.commands.deploy.get_config", return_value=agent_config),
        patch("local_console.commands.deploy.is_localhost", return_value=True),
        patch("local_console.commands.deploy.DeployFSM") as mock_gen_deploy_fsm,
        patch("local_console.commands.deploy.exec_deployment") as mock_exec_deploy,
        patch(
            "local_console.commands.deploy.module_deployment_setup",
            return_value=deployment_manifest,
        ) as mock_setup_manifest,
        patch(
            "local_console.commands.deploy.project_binary_lookup",
        ) as mock_get_path,
        patch("pathlib.Path.is_dir") as mock_check_dir,
    ):
        result = runner.invoke(app, ["-t", timeout])
        mock_agent_client.assert_called_once()
        mock_check_dir.assert_called_once()

        mock_gen_deploy_fsm.instantiate.assert_called_once_with(
            mock_agent_client.return_value.onwire_schema,
            mock_agent_client.return_value.deploy,
            None,
            ANY,
            timeout,
        )
        mock_deploy_fsm = mock_gen_deploy_fsm.instantiate.return_value

        mock_get_path.assert_called_once_with(
            ANY,
            ANY,
            None,
            False,
        )
        mock_setup_manifest.assert_called_once_with(
            ANY,
            mock_get_path.return_value,
            mock_deploy_fsm.webserver,
            ANY,
            ANY,
        )

        mock_deploy_fsm.set_manifest.assert_called_once_with(deployment_manifest)
        mock_exec_deploy.assert_called_once_with(
            mock_agent_client(),
            mock_deploy_fsm,
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
        patch("local_console.commands.deploy.is_localhost", return_value=True),
        patch("local_console.commands.deploy.Agent") as mock_agent_client,
        patch("local_console.commands.deploy.get_config", return_value=agent_config),
        patch(
            "local_console.commands.deploy.Path.is_dir", return_value=False
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
        patch("local_console.clients.agent.get_config", return_value=agent_config),
        patch(
            "local_console.clients.agent.OnWireProtocol.from_iot_spec",
            return_value=onwire_schema,
        ),
        patch("local_console.clients.agent.paho.Client"),
        patch("local_console.clients.agent.AsyncClient"),
    ):
        request_topic = MQTTTopics.ATTRIBUTES_REQ.value.replace("+", str(mqtt_req_id))

        agent = Agent()
        agent.publish = AsyncMock()
        async with agent.mqtt_scope([MQTTTopics.ATTRIBUTES_REQ.value]):
            check = await check_attributes_request(agent, request_topic, "{}")

        response_topic = request_topic.replace("request", "response")
        agent.publish.assert_called_once_with(response_topic, "{}")
        assert check


@given(deployment_manifest_strategy(), generate_agent_config())
def test_deploy_forced_webserver(
    deployment_manifest: DeploymentManifest, agent_config: AgentConfiguration
) -> None:
    with (
        patch("local_console.commands.deploy.is_localhost", return_value=False),
        patch("local_console.commands.deploy.Agent") as mock_agent_client,
        patch("local_console.commands.deploy.get_config", return_value=agent_config),
        patch("local_console.commands.deploy.is_localhost", return_value=True),
        patch("local_console.commands.deploy.DeployFSM") as mock_gen_deploy_fsm,
        patch("local_console.commands.deploy.exec_deployment") as mock_exec_deploy,
        patch(
            "local_console.commands.deploy.module_deployment_setup",
            return_value=deployment_manifest,
        ) as mock_setup_manifest,
        patch(
            "local_console.commands.deploy.project_binary_lookup",
        ) as mock_get_path,
        patch("pathlib.Path.is_dir") as mock_check_dir,
    ):
        result = runner.invoke(app, ["-f"])
        mock_agent_client.assert_called_once()
        mock_check_dir.assert_called_once()

        mock_gen_deploy_fsm.instantiate.assert_called_once_with(
            mock_agent_client.return_value.onwire_schema,
            mock_agent_client.return_value.deploy,
            None,
            True,
            ANY,
        )
        mock_deploy_fsm = mock_gen_deploy_fsm.instantiate.return_value

        mock_get_path.assert_called_once_with(
            ANY,
            ANY,
            ANY,
            ANY,
        )
        mock_setup_manifest.assert_called_once_with(
            ANY,
            mock_get_path.return_value,
            mock_deploy_fsm.webserver,
            ANY,
            ANY,
        )

        mock_deploy_fsm.set_manifest.assert_called_once_with(deployment_manifest)
        mock_exec_deploy.assert_called_once_with(
            mock_agent_client(),
            mock_deploy_fsm,
        )
        assert result.exit_code == 0


def test_project_binary_lookup_no_interpreted_wasm(tmp_path):
    with pytest.raises(FileNotFoundError):
        project_binary_lookup(tmp_path, "node", None, False)


@given(st.booleans())
def test_project_binary_lookup_no_arch(signed):

    parent = Path("some_dir")
    mod_file = parent / "node.wasm"
    with (
        patch("pathlib.Path.is_dir", return_value=True),
        patch("pathlib.Path.is_file", return_value=True),
    ):
        assert project_binary_lookup(parent, "node", None, signed) == mod_file


@pytest.mark.parametrize(
    "signed, file_name",
    [
        (False, "node.xtensa.aot"),
        (True, "node.xtensa.aot.signed"),
    ],
)
def test_project_binary_lookup_with_arch(signed, file_name, tmp_path):

    base_file = tmp_path / "node.wasm"
    base_file.touch()

    mod_file = tmp_path / file_name
    mod_file.touch()

    assert project_binary_lookup(tmp_path, "node", Target.XTENSA, signed) == mod_file


@pytest.mark.trio
@pytest.mark.parametrize(
    "errored",
    [
        False,
        True,
    ],
)
async def test_exec_deployment(errored, nursery) -> None:

    @asynccontextmanager
    async def mock_mqtt_scope(*args):
        yield True

    with (
        patch("local_console.commands.deploy.DeployFSM") as mock_fsm,
        patch("local_console.commands.deploy.stimuli_loop") as mock_stimuli,
    ):
        mock_agent = AsyncMock()
        mock_agent.mqtt_scope = mock_mqtt_scope

        mock_fsm.start = AsyncMock()
        mock_fsm.errored = errored
        mock_fsm.done = trio.Event()
        mock_stimuli.side_effect = lambda agent, fsm: fsm.done.set()

        assert await exec_deployment(mock_agent, mock_fsm, None) != errored


@given(
    st.sampled_from(OnWireProtocol),
)
@pytest.mark.trio
async def test_stimuli_proc(
    onwire_schema: OnWireProtocol,
):
    mock_fsm = AsyncMock()
    topic = MQTTTopics.ATTRIBUTES.value
    payload = {"a": "b"}
    serialized = {
        "deploymentStatus": (
            payload if onwire_schema == OnWireProtocol.EVP2 else json.dumps(payload)
        )
    }
    await stimulus_proc(topic, serialized, onwire_schema, mock_fsm)

    mock_fsm.update.assert_awaited_with(payload)
