import os
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

import allure
from hamcrest import all_of
from hamcrest import has_entry
from local_console.core.commands.ota_deploy import configuration_spec
from local_console.core.commands.ota_deploy import get_apfw_version_string
from local_console.core.config import get_config
from local_console.servers.webserver import GenericWebserver
from src.lc_adapter import LocalConsoleAdapter

from tests.matchers.is_base64 import is_base64
from tests.matchers.ota import ota_has_succeeded


@allure.parent_suite("OTA FW update version 1.4.3 to 1.5.1")
@allure.suite("FW update")
def test_ota_update(mqtt_broker: LocalConsoleAdapter) -> None:
    allure.dynamic.title("OTA update - Onwire: EVP1 - Interface v1")

    # Set EVP1
    mqtt_broker.invoke_cli("config", "set", "evp", "iot_platform", "evp1")

    # Get target firmware binary
    ota_pkg_file = Path(os.environ["FW_V1_5_PATH"])
    assert ota_pkg_file.is_file()

    # Start webserver
    config = get_config()
    with SimpleWebserver(ota_pkg_file.parent, config.webserver.port):
        # Prepare OTA update specification
        update_spec = configuration_spec(
            ota_pkg_file,
            ota_pkg_file.parent,
            config.webserver.port,
            config.webserver.host.ip_value,
        )
        update_spec.OTA.UpdateModule = "ApFw"
        version = get_apfw_version_string(ota_pkg_file.read_bytes())
        update_spec.OTA.DesiredVersion = version

        # Trigger the firmware update
        mqtt_broker.publish_configuration(
            "backdoor-EA_Main", "placeholder", update_spec.model_dump()
        )

        # Await firmware update success
        mqtt_broker.wait_configuration(
            has_entry(
                "state/backdoor-EA_Main/placeholder",
                all_of(is_base64(), ota_has_succeeded(version)),
            ),
            timeout=90,
        )


class SimpleWebserver(GenericWebserver):
    def __init__(self, directory: Path, port: int):
        super().__init__(port, True)
        self.dir = directory

    def handler(self, *args: Any, **kwargs: Any) -> SimpleHTTPRequestHandler:
        return SimpleHTTPRequestHandler(*args, directory=str(self.dir), **kwargs)
