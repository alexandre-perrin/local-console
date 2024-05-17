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
import logging
import re
import subprocess as sp
from pathlib import Path
from ssl import SSLError
from typing import Any

import allure
import paho.mqtt.client as mqtt
from devispare import EvpIotPlatform
from docker.models.containers import Container
from paho.mqtt.client import MQTTMessage
from src.interface import OnWireSchema
from src.mqtt import MQTTBroker

logger = logging.getLogger(__name__)


class LocalConsoleAdapter(MQTTBroker):
    """
    This class builds upon the MQTTBroker class from the Type 3
    system tests repository, so as to use exercise the methods
    of the Local Console CLI
    """

    def invoke_cli(self, *args: str, **kwargs: Any) -> sp.CompletedProcess:
        command = ["local-console", *args]
        logger.info(f"Running command: {' '.join(command)}")
        return sp.run(command, check=True, **kwargs)

    @staticmethod
    def iot_platform_from_schema(platform: EvpIotPlatform) -> str:
        if platform == EvpIotPlatform.EVP1:
            return "evp1"
        elif platform == EvpIotPlatform.TB:
            return "tb"
        raise NotImplementedError(f"Unknown Platform {platform}")

    def __init__(
        self, onwire_schema: OnWireSchema, certificates: Path, signing_key: Path
    ) -> None:
        super().__init__(onwire_schema, certificates)

        self.signing_key = signing_key
        self._frpc_http_container: Container | None = None

        # Configure the CLI
        platform = self.iot_platform_from_schema(self._onwire_schema.platform)
        self.invoke_cli("config", "set", "evp", "iot_platform", platform)
        self.invoke_cli(
            "config",
            "set",
            "tls",
            "ca_certificate",
            str(self.cafile.resolve()),
        )
        self.invoke_cli(
            "config",
            "set",
            "tls",
            "ca_key",
            str(self.cafile.with_suffix(".key").resolve()),
        )

    def start(
        self,
        local: bool,
        frp_host: str,
        frp_port_mqtt: int,
        frp_token: str,
        frp_port_http: int,
        frp_name_suffix: str,
    ) -> None:
        # MQTT setup
        super().start(local, frp_host, frp_port_mqtt, frp_token, frp_name_suffix)
        if not self._knock_on_broker_port(frp_host, frp_port_mqtt):
            raise ConnectionError("Could not contact MQTT broker over FRP")

        self.invoke_cli("config", "set", "mqtt", "host", frp_host)
        self.invoke_cli("config", "set", "mqtt", "port", str(frp_port_mqtt))

        # HTTP setup
        if not local:
            """
            This setup makes equal the exposed webserver port in the FRP server
            and the internal port exposed in the machine. This is required as
            the local-console's web server listens on the configured webserver
            port, and it emits deployment manifests with the server URL having
            the same port, so they must match on the local and remote ends.
            """
            self._frpc_http_container = self._start(
                name="frp-http",
                tag="frp-client",
                args={
                    "SERVICE_NAME": "http",
                    "INTERNAL_PORT": str(frp_port_http),
                    "INTERNAL_HOST": "localhost",
                    "FRP_EXTERNAL_PORT": str(frp_port_http),
                    "FRP_HOST": frp_host,
                    "FRP_TOKEN": frp_token,
                    "FRP_NAME_SUFFIX": ""
                    if not frp_name_suffix
                    else f"-{frp_name_suffix}",
                },
            )
        self.invoke_cli("config", "set", "webserver", "host", frp_host)
        self.invoke_cli("config", "set", "webserver", "port", str(frp_port_http))

    def _on_message(self, mqttc: mqtt.Client, obj: Any, msg: MQTTMessage) -> None:
        """
        This method override is preventing the agent attributes initialization
        by the original method, because such behavior is to be exhibited by the
        Local Console implementation.
        """
        topic = msg._topic.decode()

        if topic not in self._topics:
            topic = topic.rsplit("/", 1)[0] + "/+"

        self._messages[topic].append(json.loads(msg.payload))

        if not self.is_device_connected.is_set():
            result = re.search(
                r"^v1\/devices\/([^\/]+)\/attributes\/request\/(\d+)$", msg.topic
            )

            if result:
                self.is_device_connected.set()

    @allure.step("Push MDC over MQTT")
    def publish_mdc(
        self, instance: str, method: str, params: dict, reqid: int | str | None = None
    ) -> None:
        self.invoke_cli("rpc", instance, method, json.dumps(params))

    @allure.step("Push configuration over MQTT")
    def publish_configuration(
        self, instance: str, topic: str, config: dict, reqid: int | str | None = None
    ) -> None:
        self.invoke_cli(
            "config",
            "instance",
            instance,
            topic,
            json.dumps(config),
        )

    @allure.step("Build a signed WASM AoT module")
    def build_module(self, module_dir: Path) -> None:
        assert module_dir.is_dir(), "must be a directory holding a WASM module project"
        self.invoke_cli(
            "build", "--secret", str(self.signing_key), "xtensa", cwd=module_dir
        )

    @allure.step("Deploy a signed WASM AoT module")
    def deploy_module(self, module_dir: Path, timeout: int = 60) -> None:
        assert module_dir.is_dir(), "must be a directory holding a WASM module project"
        return self.invoke_cli(
            "deploy",
            "--signed",
            "--force-webserver",
            "--timeout",
            str(timeout),
            "xtensa",
            cwd=module_dir,
            capture_output=True,
            text=True,
        )

    @allure.step("Empty deployment")
    def empty_deployment(self, timeout: int = 60) -> None:
        return self.invoke_cli(
            "deploy",
            "--empty",
            "--timeout",
            str(timeout),
            capture_output=True,
            text=True,
        )

    def _knock_on_broker_port(
        self, host: str, port: int, max_attempts: int = 10
    ) -> bool:
        could_connect = False
        mqtt_c = mqtt.Client()
        mqtt_c.tls_set(
            ca_certs=str(self.cafile),
            certfile=str(self._certfile),
            keyfile=str(self._keyfile),
        )
        for _attempt in range(max_attempts):
            try:
                logger.warning(f"Attempting to connect to {host} on port {port}")
                mqtt_c.connect(host, port)
                could_connect = True
                break
            except TimeoutError as e:
                logger.warning(f"Connection attempt timed out: {e}")
            except SSLError as e:
                logger.warning(f"Connection attempt got SSL error: {e}")
                # Stop attempting as this error means that the service
                # is available on the remote end anyways.
                could_connect = True
                break

        return could_connect

    def stop(self, logs_folder: Path) -> None:
        self._stop(self._frpc_http_container, logs_folder / "frpc_http.logs")
        super().stop(logs_folder)
