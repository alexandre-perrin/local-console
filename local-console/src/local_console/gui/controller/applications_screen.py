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
import logging
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from local_console.clients.agent import Agent
from local_console.core.commands.deploy import exec_deployment
from local_console.core.commands.deploy import make_unique_module_ids
from local_console.core.commands.deploy import populate_urls_and_hashes
from local_console.core.config import get_config
from local_console.core.schemas.schemas import Deployment
from local_console.core.schemas.schemas import DeploymentManifest
from local_console.gui.driver import Driver
from local_console.gui.model.applications_screen import ApplicationsScreenModel
from local_console.gui.view.applications_screen.applications_screen import (
    ApplicationsScreenView,
)
from local_console.utils.local_network import get_my_ip_by_routing


logger = logging.getLogger(__name__)


class ApplicationsScreenController:
    """
    The `ApplicationsScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.

    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model: ApplicationsScreenModel, driver: Driver):
        self.model = model
        self.driver = driver
        self.view = ApplicationsScreenView(controller=self, model=self.model)

    def get_view(self) -> ApplicationsScreenView:
        return self.view

    def deploy(self) -> None:
        self.driver.from_sync(self.deploy_task)

    async def deploy_task(self) -> bool:
        config: AgentConfiguration = get_config()  # type:ignore
        port = config.webserver.port

        module_file = Path(self.view.ids.app_file.path)

        node = "node"
        deployment = Deployment.model_validate(
            {
                "deploymentId": "",
                "instanceSpecs": {
                    node: {"moduleId": node, "subscribe": {}, "publish": {}}
                },
                "modules": {
                    node: {
                        "entryPoint": "main",
                        "moduleImpl": "wasm",
                        "downloadUrl": "",
                        "hash": "",
                    }
                },
                "publishTopics": {},
                "subscribeTopics": {},
            }
        )

        with TemporaryDirectory(prefix="wedge_deploy_") as temporary_dir:
            tmpdir = Path(temporary_dir)
            named_module = tmpdir / "".join([node] + module_file.suffixes)
            shutil.copy(module_file, named_module)
            deployment.modules[node].downloadUrl = str(named_module)
            deployment_manifest = DeploymentManifest(deployment=deployment)

            populate_urls_and_hashes(
                deployment_manifest, get_my_ip_by_routing(), port, tmpdir
            )
            make_unique_module_ids(deployment_manifest)
            self.model.manifest = deployment_manifest

            try:
                await exec_deployment(
                    Agent(), deployment_manifest, True, tmpdir, port, 30
                )
            except Exception as e:
                logger.exception("Deployment error", exc_info=e)
                return False
            return True
