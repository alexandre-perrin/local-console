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
import hashlib
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import hypothesis.strategies as st
import pytest
import trio
from hypothesis import given
from local_console.core.camera.enums import DeployStage
from local_console.core.commands.deploy import DeployFSM
from local_console.core.commands.deploy import single_module_manifest_setup
from local_console.core.schemas.schemas import DeploymentManifest
from local_console.core.schemas.schemas import OnWireProtocol

from tests.strategies.deployment import deployment_manifest_strategy


@given(
    deployment_manifest_strategy(),
    st.sampled_from(OnWireProtocol),
)
@pytest.mark.trio
async def test_callback_on_stage_transitions(
    deploy_manifest: DeploymentManifest,
    onwire_schema: OnWireProtocol,
) -> None:
    stage_cb = AsyncMock()
    deploy_fn = AsyncMock()

    with patch("local_console.core.commands.deploy.SyncWebserver"):

        deploy_fsm = DeployFSM.instantiate(onwire_schema, deploy_fn, stage_cb)
        deploy_fsm.set_manifest(deploy_manifest)

        async with trio.open_nursery() as nursery:
            await deploy_fsm.start(nursery)
            first_stage = (
                DeployStage.WaitFirstStatus
                if onwire_schema == OnWireProtocol.EVP2
                else DeployStage.WaitAppliedConfirmation
            )
            stage_cb.assert_awaited_once_with(first_stage)
            nursery.cancel_scope.cancel()

        await deploy_fsm.check_termination(
            is_finished=True, matches=True, is_errored=False
        )
        stage_cb.assert_awaited_with(DeployStage.Done)
        assert not deploy_fsm.errored

        await deploy_fsm.check_termination(
            is_finished=False, matches=True, is_errored=True
        )
        stage_cb.assert_awaited_with(DeployStage.Error)
        assert deploy_fsm.errored


@given(
    deployment_manifest_strategy(),
)
@pytest.mark.trio
async def test_evp2_stage_transitions(
    deploy_manifest: DeploymentManifest,
) -> None:
    stage_cb = AsyncMock()
    deploy_fn = AsyncMock()

    with patch("local_console.core.commands.deploy.SyncWebserver"):

        deploy_fsm = DeployFSM.instantiate(OnWireProtocol.EVP2, deploy_fn, stage_cb)
        deploy_fsm.set_manifest(deploy_manifest)
        dep_sta_tpl = template_deploy_status_for_manifest(deploy_manifest)

        async with trio.open_nursery() as nursery:
            await deploy_fsm.start(nursery)
            first_stage = DeployStage.WaitFirstStatus
            stage_cb.assert_awaited_once_with(first_stage)

            dep_sta_tpl["reconcileStatus"] = "applying"
            await deploy_fsm.update(dep_sta_tpl)
            stage_cb.assert_awaited_with(DeployStage.WaitAppliedConfirmation)

            dep_sta_tpl["reconcileStatus"] = "ok"
            await deploy_fsm.update(dep_sta_tpl)
            stage_cb.assert_awaited_with(DeployStage.Done)

            nursery.cancel_scope.cancel()


def test_deployment_setup(tmpdir):
    origin = Path(tmpdir.join("a_module_file"))
    contents = str(uuid.uuid4())
    origin.write_text(contents)
    sha256_hash = hashlib.sha256()
    sha256_hash.update(contents.encode())
    mod_sha = sha256_hash.hexdigest()

    instance_name = "abc"
    server_add = "1.2.3.4"

    computed_mod_name = f"{instance_name}-{mod_sha[:5]}"

    with (
        patch(
            "local_console.utils.local_network.get_my_ip_by_routing",
            return_value=server_add,
        ),
    ):
        port = 8888
        webserver = Mock()
        webserver.port = port
        dm = single_module_manifest_setup(instance_name, origin, webserver)

        webserver.set_directory.assert_called_once_with(origin.parent)
        assert instance_name in dm.deployment.instanceSpecs
        assert computed_mod_name in dm.deployment.modules
        assert dm.deployment.modules[computed_mod_name].hash == mod_sha
        assert server_add in dm.deployment.modules[computed_mod_name].downloadUrl
        assert str(port) in dm.deployment.modules[computed_mod_name].downloadUrl


def template_deploy_status_for_manifest(manifest: DeploymentManifest) -> dict[str, Any]:
    deploy_id = manifest.deployment.deploymentId
    instances = list(manifest.deployment.instanceSpecs.keys())
    modules = list(manifest.deployment.modules.keys())
    return {
        "deploymentId": deploy_id,
        "reconcileStatus": "",
        "modules": {name: {"status": ""} for name in modules},
        "instances": {name: {"status": ""} for name in instances},
    }
