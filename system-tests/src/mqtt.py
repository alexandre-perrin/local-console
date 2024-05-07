import json
import re
import ssl
import threading
from collections import deque
from collections.abc import Hashable
from collections.abc import Mapping
from pathlib import Path
from time import sleep
from typing import Any
from typing import ClassVar
from typing import TypeVar

import allure
import docker
import paho.mqtt.client as mqtt
from allure_commons import _allure
from docker.models.containers import Container
from docker.models.networks import Network
from hamcrest import assert_that
from hamcrest.core.matcher import Matcher
from paho.mqtt.client import MQTT_ERR_SUCCESS
from paho.mqtt.client import MQTTMessage
from src.interface import OnWireSchema

K = TypeVar("K", bound=Hashable)

BASE_DIR = Path(__file__).parent


class MQTTBroker:
    _topics: ClassVar = [
        "v1/devices/me/telemetry",
        "v1/devices/me/attributes",
        "v1/devices/me/attributes/request/+",
        "v1/devices/me/attributes/response/+",
        "v1/devices/me/rpc/request/+",
        "v1/devices/me/rpc/response/+",
    ]

    def __init__(self, onwire_schema: OnWireSchema, certificates: Path) -> None:
        self._onwire_schema = onwire_schema

        self.cafile = certificates / "ca.crt"
        self._certfile = certificates / "pytest.crt"
        self._keyfile = certificates / "pytest.key"

        self._frpc_container: Container | None = None
        self._mqtt_container: Container | None = None

        self._network: Network | None = None

        self._mqttc = mqtt.Client()
        self._dockerc = docker.from_env()

        self._mqttc.on_connect = self._on_connect
        self._mqttc.on_message = self._on_message

        self._messages: dict[str, deque[dict]] = {}

        # It's not required to save all the messages
        # Drop left side message when queue is full (>10)

        for topic in self._topics:
            self._messages[topic] = deque(maxlen=10)

        # An event is required to not block MQTT Thread

        self.is_device_connected = threading.Event()

        self.reqid = 10020

    def _on_connect(
        self, mqttc: mqtt.Client, obj: Any, flags: dict[str, int], rc: int
    ) -> None:
        for topic in self._topics:
            with _allure.StepContext("Subscribe MQTT Topic", {"topic": topic}):
                self._mqttc.subscribe(topic)

    def _on_message(self, mqttc: mqtt.Client, obj: Any, msg: MQTTMessage) -> None:
        topic = msg._topic.decode()

        if topic not in self._topics:
            topic = topic.rsplit("/", 1)[0] + "/+"

        self._messages[topic].append(json.loads(msg.payload))

        if not self.is_device_connected.is_set():
            result = re.search(
                r"^v1\/devices\/([^\/]+)\/attributes\/request\/(\d+)$", msg.topic
            )

            if result:
                # Required to initialize the Agent
                self.publish(
                    f"v1/devices/{result.group(1)}/attributes/response/{result.group(2)}",
                    {},
                )
                self.reqid = int(result.group(2)) + 1
                self.is_device_connected.set()

    def _connect(self, host: str) -> None:
        self._mqttc.tls_set(
            ca_certs=str(self.cafile),
            certfile=str(self._certfile),
            keyfile=str(self._keyfile),
            cert_reqs=ssl.CERT_REQUIRED,
        )
        self._mqttc.tls_insecure_set(True)

        self._mqttc.connect(host=host, port=8883)

        self._mqttc.loop_start()

        while not self._mqttc.is_connected():
            sleep(1)

    def _start(
        self, name: str, tag: str, args: dict, network: str | None = None
    ) -> Container:
        self._dockerc.images.build(
            path=f"{BASE_DIR}/resources/{tag}",
            rm=True,
            tag=f"{tag}:latest",
            buildargs=args,
        )

        params = {
            "name": name,
            "image": f"{tag}:latest",
            "detach": True,
        }

        if network:
            container = self._dockerc.containers.run(
                **params,
                network=network,
            )
        else:
            container = self._dockerc.containers.run(
                **params,
                network_mode="host",
            )

        while container.attrs["State"]["Status"] != "running":
            container.reload()
            sleep(1)

        return container

    def start(self, local: bool, frp_host: str, frp_port: int, frp_token: str) -> None:

        self._mqtt_container = self._start(
            name="mqtt",
            tag="mqtt-broker",
            args={},
        )
        broker_addr = "localhost"

        if not local:
            self._frpc_container = self._start(
                name="frp",
                tag="frp-client",
                args={
                    "FRP_HOST": frp_host,
                    "FRP_EXTERNAL_PORT": str(frp_port),
                    "FRP_TOKEN": frp_token,
                    "INTERNAL_PORT": "8883",
                    "SERVICE_NAME": "mqtt",
                    "INTERNAL_HOST": broker_addr,
                    "FRP_NAME_SUFFIX": "" if not frp_name_suffix else f"-{frp_name_suffix}",
                },
            )

        self._connect(broker_addr)

    def _stop(self, container: None | Container, log_file: Path) -> None:
        if container:
            container.stop()
            container.wait()
            log_file.write_bytes(container.logs())
            container.remove()

    def stop(self, logs_folder: Path) -> None:
        self._stop(self._frpc_container, logs_folder / "frpc.logs")
        self._stop(self._mqtt_container, logs_folder / "mqtt.logs")

        if self._network:
            self._network.remove()

        self._dockerc.volumes.prune()

    @allure.step("Publish MQTT Message")
    def publish(self, topic: str, payload: dict) -> None:
        for _ in range(5):
            rc, _ = self._mqttc.publish(topic, json.dumps(payload).encode())

            if rc == MQTT_ERR_SUCCESS:
                return

            sleep(1)

        raise ConnectionError

    def wait_mdc_response(
        self, matcher: Matcher[Mapping[K, Any]], timeout: int
    ) -> None:
        with _allure.StepContext("Wait RPC Response", {"expected": str(matcher)}):
            for _ in range(timeout):
                res = self.received_rpc_response
                if res != {}:
                    break
                sleep(1)

            if not res:
                raise TimeoutError(f"MDC Response not received after {timeout}s")

            assert_that(self._onwire_schema.from_rpc(res), matcher)

    def wait_configuration(
        self, matcher: Matcher[Mapping[K, Any]], timeout: int
    ) -> None:
        err_message = None

        with _allure.StepContext("Wait Configuration", {"expected": str(matcher)}):
            for _ in range(timeout):
                res = self.received_attributes
                try:
                    assert_that(self._onwire_schema.from_config(res), matcher)
                    return

                except AssertionError as err:
                    err_message = str(err)
                    sleep(5)

        raise AssertionError(f"{err_message} after {timeout}s")

    def publish_mdc(
        self, instance: str, method: str, params: dict, reqid: int | str | None = None
    ) -> None:
        self.publish(
            f"v1/devices/me/rpc/request/{self.reqid}",
            self._onwire_schema.to_rpc(
                reqid=reqid or self.reqid,
                instance=instance,
                method=method,
                params=params,
            ),
        )
        if not reqid:
            self.reqid += 1

    def publish_configuration(
        self, instance: str, topic: str, config: dict, reqid: int | str | None = None
    ) -> None:
        self.publish(
            "v1/devices/me/attributes",
            self._onwire_schema.to_config(
                reqid=reqid or self.reqid,
                instance=instance,
                topic=topic,
                config=config,
            ),
        )
        if not reqid:
            self.reqid += 1

    def _pop_message(self, topic: str) -> dict:
        try:
            message = self._messages[topic].popleft()

            # Syntactic Sugar for Allure
            with _allure.StepContext(
                "Received MQTT Message",
                {"topic": topic, "payload": json.dumps(message)},
            ):
                return message

        except Exception:
            return {}

    @property
    def received_telemetry(self) -> dict:
        return self._pop_message("v1/devices/me/telemetry")

    @property
    def received_attributes(self) -> dict:
        return self._pop_message("v1/devices/me/attributes")

    @property
    def received_attributes_request(self) -> dict:
        return self._pop_message("v1/devices/me/attributes/request/+")

    @property
    def received_attributes_response(self) -> dict:
        return self._pop_message("v1/devices/me/attributes/response/+")

    @property
    def received_rpc_request(self) -> dict:
        return self._pop_message("v1/devices/me/rpc/request/+")

    @property
    def received_rpc_response(self) -> dict:
        return self._pop_message("v1/devices/me/rpc/response/+")
