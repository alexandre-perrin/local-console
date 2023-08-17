import json
import logging
from collections.abc import Callable

import paho.mqtt.client as mqtt
from wedge_cli.utils.enums import GetObjects

logger = logging.getLogger(__name__)


def on_connect(topic: str) -> Callable:
    def __callback(
        client: mqtt.Client,
        userdata: None,
        flags: dict,
        rc: str,
    ) -> None:
        client.subscribe(topic)

    return __callback


def on_message_return_payload() -> Callable:
    def __callback(client: mqtt.Client, userdata: None, msg: mqtt.MQTTMessage) -> None:
        payload = json.loads(msg.payload)
        logger.info(payload)

    return __callback


def on_message_instance(instance_id: str) -> Callable:
    def __callback(client: mqtt.Client, userdata: None, msg: mqtt.MQTTMessage) -> None:
        instances = json.loads(msg.payload)["deploymentStatus"]["instances"]
        for instance in list(instances.keys()):
            if instance == instance_id:
                logger.info(instances[str(instance)])

    return __callback


def connect_client_loop(connect_callback: Callable, message_callback: Callable) -> None:
    client: mqtt.Client = mqtt.Client()
    client.on_connect = connect_callback
    client.on_message = message_callback

    client.connect("localhost", 1884, 60)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        # avoids ugly logs when killing the loop
        pass


def get_deployment(**kwargs: dict) -> None:
    connect_client_loop(
        connect_callback=on_connect(topic="v1/devices/me/attributes"),
        message_callback=on_message_return_payload(),
    )


def get_telemetry(**kwargs: dict) -> None:
    connect_client_loop(
        connect_callback=on_connect(topic="v1/devices/me/telemetry"),
        message_callback=on_message_return_payload(),
    )


def get_instance(**kwargs: dict) -> None:
    connect_client_loop(
        connect_callback=on_connect(topic="v1/devices/me/attributes"),
        message_callback=on_message_instance(kwargs["instance_id"][0]),
    )


GET_COMMANDS = {
    GetObjects.DEPLOYMENT: get_deployment,
    GetObjects.TELEMETRY: get_telemetry,
    GetObjects.INSTANCE: get_instance,
}


def get(**kwargs: dict) -> None:
    GET_COMMANDS[GetObjects(kwargs["get_action"])](**kwargs)
