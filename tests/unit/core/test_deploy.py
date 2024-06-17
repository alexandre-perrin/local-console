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
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import hypothesis.strategies as st
import pytest
from hypothesis import given
from local_console.clients.agent import Agent
from local_console.core.commands.deploy import DeployFSM
from local_console.core.commands.deploy import DeployStage
from local_console.core.schemas.schemas import AgentConfiguration
from local_console.core.schemas.schemas import DeploymentManifest
from local_console.core.schemas.schemas import OnWireProtocol

from tests.strategies.configs import generate_agent_config
from tests.strategies.configs import generate_valid_port_number
from tests.strategies.deployment import deployment_manifest_strategy


@given(
    generate_agent_config(),
    generate_valid_port_number(),
    deployment_manifest_strategy(),
    st.sampled_from(OnWireProtocol),
)
@pytest.mark.trio
async def test_callback_on_stage_transitions(
    agent_config: AgentConfiguration,
    port: int,
    deploy_manifest: DeploymentManifest,
    onwire_schema: OnWireProtocol,
) -> None:
    with (
        patch(
            "local_console.clients.agent.OnWireProtocol.from_iot_spec",
            return_value=onwire_schema,
        ),
        patch("local_console.clients.agent.get_config", return_value=agent_config),
        patch(
            "local_console.core.commands.deploy.Agent.initialize_handshake",
            return_value=AsyncMock(),
        ),
        patch("local_console.core.commands.deploy.AsyncWebserver"),
        # patch("local_console.core.commands.deploy.Agent.mqtt_scope", return_value=AsyncMock()),
        patch("local_console.clients.agent.paho.Client"),
        patch("local_console.clients.agent.AsyncClient"),
        patch("local_console.clients.agent.Agent.publish"),
    ):
        stage_cb = MagicMock()
        agent = Agent()
        deploy_fsm = DeployFSM.instantiate(agent, deploy_manifest, stage_cb)
        stage_cb.assert_called_once_with(DeployStage.WaitFirstStatus)

        deploy_fsm.check_termination(is_finished=True, matches=True, is_errored=False)
        stage_cb.assert_called_with(DeployStage.Done)
        assert not deploy_fsm.errored

        deploy_fsm.check_termination(is_finished=False, matches=True, is_errored=True)
        stage_cb.assert_called_with(DeployStage.Error)
        assert deploy_fsm.errored
