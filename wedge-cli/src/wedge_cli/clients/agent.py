import json
import logging
import random
import sys
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

import paho.mqtt.client as paho
from paho.mqtt.client import MQTT_ERR_SUCCESS
from wedge_cli.utils.config import get_config

logger = logging.getLogger(__name__)

start_time: float


class Agent:
    DEPLOYMENT_TOPIC = "v1/devices/me/attributes"
    # TODO: get reqid from mqtt
    REQUEST_TOPIC = "v1/devices/me/attributes/response/10003"
    TELEMETRY = "v1/devices/me/telemetry"

    def __init__(self) -> None:
        config_parse = get_config()
        self.mqttc = paho.Client()
        self.mqttc.connect(
            config_parse["mqtt"]["host"], int(config_parse["mqtt"]["port"])
        )
        self._on_connect()

    def _on_connect(self) -> None:
        mqtt_msg_info = self.mqttc.publish(self.REQUEST_TOPIC, "")
        rc, _ = mqtt_msg_info
        if rc != MQTT_ERR_SUCCESS:
            logger.error("Error on MQTT handshake with agent")

    def _on_connect_subscribe_callback(self, topic: str) -> Callable:
        def __callback(
            client: paho.Client,
            userdata: Any,
            flags: dict,
            rc: str,
        ) -> None:
            self.mqttc.subscribe(topic)

        return __callback

    def _on_message_return_payload(self) -> Callable:
        def __callback(
            client: paho.Client, userdata: Any, msg: paho.MQTTMessage
        ) -> None:
            payload = json.loads(msg.payload)
            if payload:
                try:
                    print(payload, flush=True)
                except (BrokenPipeError, OSError):
                    pass
            else:
                logger.debug("Empty message arrived")

        return __callback

    def _on_message_logs(self, instance_id: str, timeout: int) -> Callable:
        global start_time
        start_time = time.time()

        def __callback(
            client: paho.Client, userdata: Any, msg: paho.MQTTMessage
        ) -> None:
            payload = json.loads(msg.payload)
            logs = defaultdict(list)
            if "device/log" in list(payload.keys()):
                for log in payload["device/log"]:
                    logs[log["app"]].append(log)
                if instance_id in list(logs.keys()):
                    globals()["start_time"] = time.time()
                    for instance_log in logs[instance_id]:
                        print(instance_log)
            elif (time.time() - globals()["start_time"]) > timeout:
                logger.info(
                    f"No logs found for {instance_id}. Please check the instance id is correct"
                )
                sys.exit()

        return __callback

    def _on_message_telemetry(self) -> Callable:
        def __callback(
            client: paho.Client, userdata: Any, msg: paho.MQTTMessage
        ) -> None:
            payload = json.loads(msg.payload)
            if "device/log" in list(payload.keys()):
                pass
            else:
                print(payload, flush=True)

        return __callback

    def _on_message_instance(self, instance_id: str) -> Callable:
        def __callback(
            client: paho.Client, userdata: Any, msg: paho.MQTTMessage
        ) -> None:
            payload = json.loads(msg.payload)
            if (
                "deploymentStatus" not in payload
                or "instances" not in payload["deploymentStatus"]
            ):
                return
            instances = payload["deploymentStatus"]["instances"]

            if instance_id in list(instances.keys()):
                print(instances[str(instance_id)])
            else:
                logger.info(
                    f"Module instance not found. The available module instance are {list(instances.keys())}"
                )
                sys.exit()

        return __callback

    def deploy(self, deployment: str) -> None:
        mqtt_msg_info = self.mqttc.publish(self.DEPLOYMENT_TOPIC, deployment)
        rc, _ = mqtt_msg_info
        if rc != MQTT_ERR_SUCCESS:
            logger.error("Error on MQTT deploy to agent")

    def rpc(self, instance_id: str, method: str, params: str) -> None:
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
        mqtt_msg_info = self.mqttc.publish(RPC_TOPIC, payload=payload)
        rc, _ = mqtt_msg_info
        if rc != MQTT_ERR_SUCCESS:
            logger.error("Error on MQTT publish agent logs")

    def get_logs(self, instance_id: str, timeout: int) -> None:
        self._loop_client(
            connect_callback=self._on_connect_subscribe_callback(topic=self.TELEMETRY),
            message_callback=self._on_message_logs(instance_id, timeout),
        )

    def _loop_client(
        self, connect_callback: Callable, message_callback: Callable
    ) -> None:
        self.mqttc.on_connect = connect_callback
        self.mqttc.on_message = message_callback
        try:
            self.mqttc.loop_forever()
        except KeyboardInterrupt:
            # avoids ugly logs when killing the loop
            pass

    def get_deployment(self, **kwargs: dict) -> None:
        self._loop_client(
            connect_callback=self._on_connect_subscribe_callback(
                topic=self.DEPLOYMENT_TOPIC
            ),
            message_callback=self._on_message_return_payload(),
        )

    def get_telemetry(self, **kwargs: dict) -> None:
        self._loop_client(
            connect_callback=self._on_connect_subscribe_callback(topic=self.TELEMETRY),
            message_callback=self._on_message_telemetry(),
        )

    def get_instance(self, **kwargs: dict) -> None:
        self._loop_client(
            connect_callback=self._on_connect_subscribe_callback(
                topic=self.DEPLOYMENT_TOPIC
            ),
            message_callback=self._on_message_instance(kwargs["instance_id"][0]),
        )
