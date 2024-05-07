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

    def __init__(self, onwire_schema: OnWireSchema, certificates: Path) -> None:
        super().__init__(onwire_schema, certificates)

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

    def start(self, local: bool, frp_host: str, frp_port_mqtt: int, frp_token: str) -> None:
        super().start(local, frp_host, frp_port_mqtt, frp_token)
        if not self._knock_on_broker_port(frp_host, frp_port_mqtt):
            raise ConnectionError("Could not contact MQTT broker over FRP")

        self.invoke_cli("config", "set", "mqtt", "host", frp_host)
        self.invoke_cli("config", "set", "mqtt", "port", str(frp_port_mqtt))

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
