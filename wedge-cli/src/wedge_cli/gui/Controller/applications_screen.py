import logging
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import trio
from wedge_cli.clients.agent import Agent
from wedge_cli.commands.deploy import DeployFSM
from wedge_cli.commands.deploy import make_unique_module_ids
from wedge_cli.commands.deploy import populate_urls_and_hashes
from wedge_cli.core.config import get_config
from wedge_cli.core.schemas import Deployment
from wedge_cli.core.schemas import DeploymentManifest
from wedge_cli.gui.driver import Driver
from wedge_cli.gui.Model.applications_screen import ApplicationsScreenModel
from wedge_cli.gui.View.ApplicationsScreen.applications_screen import (
    ApplicationsScreenView,
)
from wedge_cli.servers.webserver import AsyncWebserver
from wedge_cli.utils.local_network import get_my_ip_by_routing


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
        module = Path(self.view.ids.lbl_app_path.text)

        self.driver.from_sync(self.deploy_task, module)

    async def deploy_task(self, module_file: Path) -> bool:
        success = False
        config = get_config()
        ephemeral_agent = Agent()

        webserver_port = config.webserver.port
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
            manifest = DeploymentManifest(deployment=deployment)

            # binaries are assumed to be signed already
            populate_urls_and_hashes(
                manifest, get_my_ip_by_routing(), webserver_port, tmpdir
            )
            make_unique_module_ids(manifest)
            self.model.manifest = manifest

            deploy_fsm = DeployFSM(ephemeral_agent, manifest)
            with trio.move_on_after(15) as timeout_scope:
                async with (
                    ephemeral_agent.mqtt_scope(
                        [Agent.REQUEST_TOPIC, Agent.ATTRIBUTES_TOPIC]
                    ),
                    AsyncWebserver(tmpdir, webserver_port, None, True),
                ):
                    assert ephemeral_agent.nursery  # make mypy happy

                    ephemeral_agent.nursery.start_soon(deploy_fsm.message_task)
                    await deploy_fsm.done.wait()
                    success = True
                    ephemeral_agent.async_done()

            if timeout_scope.cancelled_caught:
                logger.error("Timeout when sending modules.")

        return success
