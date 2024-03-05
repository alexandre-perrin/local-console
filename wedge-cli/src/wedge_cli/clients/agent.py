import base64
import json
import logging
import random
import re
import traceback
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from typing import Any
from typing import Callable
from typing import Optional

import paho.mqtt.client as paho
import trio
from exceptiongroup import catch
from paho.mqtt.client import MQTT_ERR_SUCCESS
from wedge_cli.clients.trio_paho_mqtt import AsyncClient
from wedge_cli.core.camera import Camera
from wedge_cli.core.camera import MQTTTopics
from wedge_cli.core.config import config_paths
from wedge_cli.core.config import get_config
from wedge_cli.core.schemas import AgentConfiguration
from wedge_cli.core.schemas import DesiredDeviceConfig
from wedge_cli.core.schemas import OnWireProtocol
from wedge_cli.utils.local_network import is_localhost
from wedge_cli.utils.timing import TimeoutBehavior
from wedge_cli.utils.tls import ensure_certificate_pair_exists
from wedge_cli.utils.tls import get_random_identifier

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self) -> None:
        self.client: Optional[AsyncClient] = None
        self.nursery: Optional[trio.Nursery] = None

        config_parse: AgentConfiguration = get_config()
        self._host = config_parse.mqtt.host.ip_value
        self._port = config_parse.mqtt.port

        client_id = f"cli-client-{random.randint(0, 10**7)}"
        self.mqttc = paho.Client(clean_session=True, client_id=client_id)

        # For initializing the camera, capturing the on-wire protocol
        self.onwire_schema: Optional[OnWireProtocol] = None

        self.configure_tls(config_parse)

    def configure_tls(self, agent_config: AgentConfiguration) -> None:
        tls_conf = agent_config.tls
        if not (tls_conf.ca_certificate and tls_conf.ca_key):
            return

        cli_cert_path, cli_key_path = config_paths.cli_cert_pair
        ensure_certificate_pair_exists(
            get_random_identifier("wedge-cli-"), cli_cert_path, cli_key_path, tls_conf
        )

        self.mqttc.tls_set(
            ca_certs=str(tls_conf.ca_certificate),
            certfile=str(cli_cert_path),
            keyfile=str(cli_key_path),
        )

        # No server validation is necessary if the server is localhost
        # This spares us from needing to setup custom name resolution for
        # complying with TLS' Subject Common Name matching.
        self.mqttc.tls_insecure_set(is_localhost(agent_config.mqtt.host.ip_value))

    def async_done(self) -> None:
        assert self.nursery
        assert self.client
        self.client.disconnect()
        self.nursery.cancel_scope.cancel()

    def _on_message_print_payload(self) -> Callable:
        async def __task(cs: trio.CancelScope) -> None:
            assert self.client is not None
            async for msg in self.client.messages():
                payload = json.loads(msg.payload.decode())
                if payload:
                    print(payload, flush=True)
                else:
                    logger.debug("Empty message arrived")

        return __task

    def _on_message_logs(self, instance_id: str, timeout: int) -> Callable:
        async def __task(cs: trio.CancelScope) -> None:
            assert self.client is not None
            with trio.move_on_after(timeout) as time_cs:
                async for msg in self.client.messages():
                    payload = json.loads(msg.payload.decode())
                    logs = defaultdict(list)
                    if "values" in payload:
                        payload = payload["values"]
                    if "device/log" in payload.keys():
                        for log in payload["device/log"]:
                            logs[log["app"]].append(log)
                        if instance_id in logs.keys():
                            time_cs.deadline += timeout
                            for instance_log in logs[instance_id]:
                                print(instance_log)

            if time_cs.cancelled_caught:
                logger.error(
                    f"No logs received for {instance_id} within {timeout} seconds. Please check the instance id is correct"
                )
                cs.cancel()

        return __task

    def _on_message_telemetry(self) -> Callable:
        async def __task(cs: trio.CancelScope) -> None:
            assert self.client is not None
            async for msg in self.client.messages():
                payload = json.loads(msg.payload.decode())
                if payload:
                    to_print = {
                        key: val
                        for key, val in payload.items()
                        if "device/log" not in key
                    }
                    print(to_print, flush=True)

        return __task

    def _on_message_instance(self, instance_id: str) -> Callable:
        async def __task(cs: trio.CancelScope) -> None:
            assert self.client is not None
            async for msg in self.client.messages():
                payload = json.loads(msg.payload.decode())
                if (
                    "deploymentStatus" not in payload
                    or "instances" not in payload["deploymentStatus"]
                ):
                    continue

                instances = payload["deploymentStatus"]["instances"]
                if instance_id in instances.keys():
                    print(instances[instance_id])
                else:
                    logger.info(
                        f"Module instance not found. The available module instance are {list(instances.keys())}"
                    )
                    cs.cancel()

        return __task

    async def determine_onwire_schema(self) -> None:
        camera_state = Camera()
        # This takes care of ensuring the device reports its state
        # with bounded periodicity (expect to receive a message within 4 seconds)
        timeout = 4
        # Configure the device to emit status reports twice
        # as often as the timeout expiration, to ensure that
        # random deviations in report perioding make the timer
        # to expire unnecessarily.
        set_periodic_reports = partial(self.set_periodic_reports, int(timeout / 2))
        periodic_reports = TimeoutBehavior(4, set_periodic_reports)

        async with self.mqtt_scope(
            [
                MQTTTopics.ATTRIBUTES_REQ.value,
                MQTTTopics.TELEMETRY.value,
                MQTTTopics.RPC_RESPONSES.value,
                MQTTTopics.ATTRIBUTES.value,
            ]
        ):
            assert self.nursery
            assert self.client  # appease mypy

            periodic_reports.spawn_in(self.nursery)
            async for msg in self.client.messages():
                attributes_available = await check_attributes_request(
                    self, msg.topic, msg.payload.decode()
                )
                if attributes_available:
                    camera_state.attributes_available = True

                payload = json.loads(msg.payload)
                camera_state.process_incoming(msg.topic, payload)

                if camera_state.is_ready:
                    periodic_reports.tap()
                    break
            self.async_done()

        self.onwire_schema = camera_state.onwire_schema

    async def set_periodic_reports(self, report_interval: int) -> None:
        await self.device_configure(
            DesiredDeviceConfig(
                reportStatusIntervalMax=report_interval,
                reportStatusIntervalMin=min(report_interval, 1),
            )
        )

    async def deploy(self, deployment: str) -> None:
        await self.publish(MQTTTopics.ATTRIBUTES.value, payload=deployment)

    async def rpc(self, instance_id: str, method: str, params: str) -> None:
        reqid = str(random.randint(0, 10**8))
        RPC_TOPIC = f"v1/devices/me/rpc/request/{reqid}"
        message: dict = {
            "method": "ModuleMethodCall",
            "params": {
                "direct-command-request": {
                    "reqid": f"{reqid}",
                    "method": f"{method}",
                    "instance": f"{instance_id}",
                    "params": f"{params}",
                }
            },
        }
        payload = json.dumps(message)
        logger.debug(f"payload: {payload}")
        await self.publish(RPC_TOPIC, payload=payload)

    async def configure(self, instance_id: str, topic: str, config: str) -> None:
        if self.onwire_schema is None:
            logger.error(
                "Cannot send a configuration message without determining the camera's on-wire protocol version"
            )
            raise SystemExit

        # The following stanza matches the implementation at:
        # https://github.com/midokura/wedge-agent/blob/ee08d254658177ddfa3f75b7d1f09922104a2427/src/libwedge-agent/instance_config.c#L324
        if self.onwire_schema == OnWireProtocol.EVP1:
            config = base64.b64encode(config.encode("utf-8")).decode("utf-8")

        message: dict = {f"configuration/{instance_id}/{topic}": config}
        payload = json.dumps(message)
        logger.debug(f"payload: {payload}")
        await self.publish(MQTTTopics.ATTRIBUTES.value, payload=payload)

    async def device_configure(
        self, desired_device_config: DesiredDeviceConfig
    ) -> None:
        """
        :param config: Configuration of the module instance.
        """
        message: dict = {
            "desiredDeviceConfig": {
                "desiredDeviceConfig": {
                    "configuration/$agent/report-status-interval-max": desired_device_config.reportStatusIntervalMax,
                    "configuration/$agent/report-status-interval-min": desired_device_config.reportStatusIntervalMin,
                    "configuration/$agent/configuration-id": "",
                    "configuration/$agent/registry-auth": {},
                }
            }
        }
        payload = json.dumps(message)
        logger.debug(f"payload: {payload}")
        await self.publish(MQTTTopics.ATTRIBUTES.value, payload=payload)

    async def loop_client(
        self, subs_topics: list[str], driver_task: Callable, message_task: Callable
    ) -> None:
        async with self.mqtt_scope(subs_topics):
            assert self.nursery is not None
            cs = self.nursery.cancel_scope
            self.nursery.start_soon(message_task, cs)
            self.nursery.start_soon(driver_task, cs)

    @asynccontextmanager
    async def mqtt_scope(self, subs_topics: list[str]) -> AsyncIterator[None]:
        async with guarded_nursery() as nursery:
            self.nursery = nursery
            self.client = AsyncClient(self.mqttc, self.nursery)

            self.client.connect(self._host, self._port)
            for topic in subs_topics:
                self.client.subscribe(topic)

            yield

    async def publish(self, topic: str, payload: str) -> None:
        assert self.client is not None
        msg_info = await self.client.publish_and_wait(topic, payload=payload)
        if msg_info[0] != MQTT_ERR_SUCCESS:
            logger.error("Error on MQTT publish agent logs")
            raise ConnectionError

    def _loop_forever(self, subs_topics: list[str], message_task: Callable) -> None:
        async def _driver_task(_cs: trio.CancelScope) -> None:
            await trio.sleep_forever()

        trio.run(self.loop_client, subs_topics, _driver_task, message_task)

    async def request_instance_logs(self, instance_id: str) -> None:
        async with self.mqtt_scope([]):
            await self.rpc(instance_id, "$agent/set", '{"log_enable": true}')
            self.async_done()

    def get_instance_logs(self, instance_id: str, timeout: int) -> None:
        self._loop_forever(
            subs_topics=[MQTTTopics.TELEMETRY.value],
            message_task=self._on_message_logs(instance_id, timeout),
        )

    def get_deployment(self) -> None:
        self._loop_forever(
            subs_topics=[MQTTTopics.ATTRIBUTES.value],
            message_task=self._on_message_print_payload(),
        )

    def get_telemetry(self) -> None:
        self._loop_forever(
            subs_topics=[MQTTTopics.TELEMETRY.value],
            message_task=self._on_message_telemetry(),
        )

    def get_instance(self, instance_id: str) -> None:
        self._loop_forever(
            subs_topics=[MQTTTopics.ATTRIBUTES.value],
            message_task=self._on_message_instance(instance_id),
        )


@asynccontextmanager
async def guarded_nursery() -> AsyncIterator[trio.Nursery]:
    with catch(
        {
            Exception: handle_task_exceptions,
        }
    ):
        async with trio.open_nursery() as nursery:
            yield nursery


def handle_task_exceptions(excgroup: Any) -> None:
    # The 'Any' annotation is used to silence mypy,
    # as it is not raising a helpful error.
    num_exceptions = len(excgroup.exceptions)
    logger.error(
        "%d Exception%s occurred, listed below:",
        num_exceptions,
        "s" if num_exceptions else "",
    )
    for e in excgroup.exceptions:
        exc_desc_lines = traceback.format_exception_only(type(e), e)
        exc_desc = "".join(exc_desc_lines).rstrip()
        logger.error("Exception: %s", exc_desc)


async def check_attributes_request(agent: Agent, topic: str, payload: str) -> bool:
    """
    Checks that a given MQTT message (as provided by its topic and payload)
    conveys a request from the device's agent for data attributes set in the
    MQTT broker.
    """
    got_request = False
    result = re.search(r"^v1/devices/me/attributes/request/(\d+)$", topic)
    if result:
        got_request = True
        req_id = result.group(1)
        logger.debug(
            "Got attribute request (id=%s) with payload: '%s'",
            req_id,
            payload,
        )
        await agent.publish(
            f"v1/devices/me/attributes/response/{req_id}",
            "{}",
        )
    return got_request
