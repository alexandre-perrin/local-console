import logging

import paho.mqtt.client as paho
from paho.mqtt.client import MQTT_ERR_SUCCESS

logger = logging.getLogger(__name__)


class Agent:
    DEPLOYMENT_TOPIC = "v1/devices/me/attributes"
    REQUEST_TOPIC = "v1/devices/me/attributes/response/10002"

    def __init__(self, mqtt_url: str = "localhost", mqtt_port: int = 1883) -> None:
        self.mqttc = paho.Client()
        self.mqttc.connect(mqtt_url, mqtt_port)
        self._on_connect()

    def _on_connect(self) -> None:
        mqtt_msg_info = self.mqttc.publish(self.REQUEST_TOPIC, "")
        rc, _ = mqtt_msg_info
        if rc != MQTT_ERR_SUCCESS:
            logger.error("Error on MQTT handshake with agent")

    def deploy(self, deployment_fp: str) -> None:
        with open(deployment_fp, "rb") as f:
            deployment = f.read()
        mqtt_msg_info = self.mqttc.publish(self.DEPLOYMENT_TOPIC, deployment)
        rc, _ = mqtt_msg_info
        if rc != MQTT_ERR_SUCCESS:
            logger.error("Error on MQTT deploy to agent")


agent = Agent()
