import json
import logging
import sys
from collections.abc import Callable

import paho.mqtt.client as paho
from paho.mqtt.client import MQTT_ERR_SUCCESS
from wedge_cli.utils.config import get_config

logger = logging.getLogger(__name__)


class Agent:
    DEPLOYMENT_TOPIC = "v1/devices/me/attributes"
    REQUEST_TOPIC = "v1/devices/me/attributes/response/10002"
    TELEMETRY = "v1/devices/me/telemetry"

    def __init__(self) -> None:
        config = get_config()
        self.mqttc = paho.Client()
        self.mqttc.connect(config["mqtt"]["host"], int(config["mqtt"]["port"]))
        self._on_connect()

    def _on_connect(self) -> None:
        mqtt_msg_info = self.mqttc.publish(self.REQUEST_TOPIC, "")
        rc, _ = mqtt_msg_info
        if rc != MQTT_ERR_SUCCESS:
            logger.error("Error on MQTT handshake with agent")

    def _on_connect_subscribe_callback(self, topic: str) -> Callable:
        def __callback(
            client: paho.Client,
            userdata: None,
            flags: dict,
            rc: str,
        ) -> None:
            self.mqttc.subscribe(topic)

        return __callback

    def _on_message_return_payload(self) -> Callable:
        def __callback(
            client: paho.Client, userdata: None, msg: paho.MQTTMessage
        ) -> None:
            payload = json.loads(msg.payload)
            print(payload)

        return __callback

    def _on_message_instance(self, instance_id: str) -> Callable:
        def __callback(
            client: paho.Client, userdata: None, msg: paho.MQTTMessage
        ) -> None:
            instances = json.loads(msg.payload)["deploymentStatus"]["instances"]

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
            message_callback=self._on_message_return_payload(),
        )

    def get_instance(self, **kwargs: dict) -> None:
        self._loop_client(
            connect_callback=self._on_connect_subscribe_callback(
                topic=self.DEPLOYMENT_TOPIC
            ),
            message_callback=self._on_message_instance(kwargs["instance_id"][0]),
        )


agent = Agent()
