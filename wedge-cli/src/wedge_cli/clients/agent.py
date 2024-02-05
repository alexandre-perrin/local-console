import base64
import json
import logging
import random
import traceback
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from typing import Callable
from typing import Optional

import paho.mqtt.client as paho
import trio
from exceptiongroup import catch
from paho.mqtt.client import MQTT_ERR_SUCCESS
from wedge_cli.utils.config import get_config
from wedge_cli.utils.schemas import AgentConfiguration
from wedge_cli.utils.trio_paho_mqtt import AsyncClient

logger = logging.getLogger(__name__)


class Agent:
    DEPLOYMENT_TOPIC = "v1/devices/me/attributes"
    # TODO: get reqid from mqtt
    REQUEST_TOPIC = "v1/devices/me/attributes/response/10003"
    TELEMETRY = "v1/devices/me/telemetry"

    def __init__(self) -> None:
        self.mqttc = paho.Client()
        self.client: Optional[AsyncClient] = None
        self.nursery: Optional[trio.Nursery] = None

        config_parse: AgentConfiguration = get_config()
        self._host = config_parse.mqtt.host.ip_value
        self._port = config_parse.mqtt.port

    def async_done(self) -> None:
        assert self.nursery
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

    def deploy(self, deployment: str) -> None:
        mqtt_msg_info = self.mqttc.publish(self.DEPLOYMENT_TOPIC, deployment)
        rc, _ = mqtt_msg_info
        if rc != MQTT_ERR_SUCCESS:
            logger.error("Error on MQTT deploy to agent")

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
        """
        :param config: Configuration of the module instance.
        """
        config = base64.b64encode(config.encode("utf-8")).decode("utf-8")
        message: dict = {f"configuration/{instance_id}/{topic}": config}
        payload = json.dumps(message)
        logger.debug(f"payload: {payload}")
        await self.publish(self.DEPLOYMENT_TOPIC, payload=payload)


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
            subs_topics=[self.TELEMETRY],
            message_task=self._on_message_logs(instance_id, timeout),
        )

    def get_deployment(self) -> None:
        self._loop_forever(
            subs_topics=[self.DEPLOYMENT_TOPIC],
            message_task=self._on_message_print_payload(),
        )

    def get_telemetry(self) -> None:
        self._loop_forever(
            subs_topics=[self.TELEMETRY],
            message_task=self._on_message_telemetry(),
        )

    def get_instance(self, instance_id: str) -> None:
        self._loop_forever(
            subs_topics=[self.DEPLOYMENT_TOPIC],
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
