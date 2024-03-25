import json
import logging
import shutil
from base64 import b64encode
from pathlib import Path
from pathlib import PurePosixPath
from tempfile import TemporaryDirectory

import trio
from cryptography.hazmat.primitives import hashes
from wedge_cli.clients.agent import Agent
from wedge_cli.core.camera import MQTTTopics
from wedge_cli.core.config import get_config
from wedge_cli.gui.driver import Driver
from wedge_cli.gui.Model.ai_model_screen import AIModelScreenModel
from wedge_cli.gui.View.AIModelScreen.ai_model_screen import (
    AIModelScreenView,
)
from wedge_cli.servers.webserver import AsyncWebserver
from wedge_cli.utils.local_network import get_my_ip_by_routing


logger = logging.getLogger(__name__)


class AIModelScreenController:
    """
    The `AIModelScreenController` class represents a controller implementation.
    Coordinates work of the view with the model.

    The controller implements the strategy pattern. The controller connects to
    the view to control its actions.
    """

    def __init__(self, model: AIModelScreenModel, driver: Driver):
        self.model = model
        self.driver = driver
        self.view = AIModelScreenView(controller=self, model=self.model)

    def get_view(self) -> AIModelScreenView:
        return self.view

    def deploy(self) -> None:
        self.view.ids.btn_ota_file.disabled = True
        self.driver.from_sync(self.deploy_task, self.model.model_file)

    async def deploy_task(self, package_file: Path) -> None:
        config = get_config()
        ephemeral_agent = Agent()
        webserver_port = config.webserver.port

        with TemporaryDirectory(prefix="wedge_deploy_") as temporary_dir:
            tmp_dir = Path(temporary_dir)
            tmp_module = tmp_dir / package_file.name
            shutil.copy(package_file, tmp_module)
            spec = configuration_spec(tmp_module, tmp_dir, webserver_port)

            # In my tests, the "Updating" phase may take this long:
            timeout_secs = 90
            with trio.move_on_after(timeout_secs) as timeout_scope:
                async with (
                    ephemeral_agent.mqtt_scope(
                        [MQTTTopics.ATTRIBUTES_REQ.value, MQTTTopics.ATTRIBUTES.value]
                    ),
                    AsyncWebserver(tmp_dir, webserver_port, None, True),
                ):
                    assert ephemeral_agent.nursery  # make mypy happy
                    await ephemeral_agent.configure(
                        "backdoor-EA_Main", "placeholder", json.dumps(spec)
                    )
                    while True:
                        await self.model.ota_event()
                        timeout_scope.deadline += timeout_secs
                        if self.model.ota_status.get("UpdateStatus") in (
                            "Done",
                            "Failed",
                        ):
                            break

            if timeout_scope.cancelled_caught:
                self.view.notify_deploy_timeout()
                logger.error("Timeout when sending modules.")


def get_package_hash(package_file: Path) -> str:
    digest = hashes.Hash(hashes.SHA256())
    digest.update(package_file.read_bytes())
    return b64encode(digest.finalize()).decode()


def configuration_spec(
    package_file: Path, webserver_root: Path, webserver_port: int
) -> dict[str, dict[str, str]]:
    file_hash = get_package_hash(package_file)
    ip_addr = get_my_ip_by_routing()
    rel_path = PurePosixPath(package_file.relative_to(webserver_root))
    url = f"http://{ip_addr}:{webserver_port}/{rel_path}"
    return {
        "OTA": {
            "UpdateModule": "DnnModel",
            "DesiredVersion": "0207000000010101",
            "PackageUri": url,
            "HashValue": file_hash,
        }
    }
