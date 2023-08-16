import json
import logging
from collections.abc import Callable

import paho.mqtt.client as mqtt
from wedge_cli.utils.enums import GetObjects

logger = logging.getLogger(__name__)


def on_connect(topic: str) -> Callable:
    def callback(
        client: mqtt.Client,
        userdata: None,
        flags: dict,
        rc: str,
    ) -> None:
        client.subscribe(topic)

    return callback


def on_message_return_payload() -> Callable:
    def callback(client: mqtt.Client, userdata: None, msg: mqtt.MQTTMessage) -> None:
        payload = json.loads(msg.payload)
        logger.info(payload)

    return callback


def on_message_instance(instance_id: str) -> Callable:
    def callback(client: mqtt.Client, userdata: None, msg: mqtt.MQTTMessage) -> None:
        instances = json.loads(msg.payload)["deploymentStatus"]["instances"]
        for instance in list(instances.keys()):
            if instance == instance_id:
                logger.info(instances[str(instance)])

    return callback


def connect_client_loop(connect_callback: Callable, message_callback: Callable) -> None:
    client: mqtt.Client = mqtt.Client()
    client.on_connect = connect_callback
    client.on_message = message_callback

    client.connect("localhost", 1883, 60)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        # avoids ugly logs when killing the loop
        pass


def get_deployment() -> None:
    connect_client_loop(
        connect_callback=on_connect(topic="v1/devices/me/attributes"),
        message_callback=on_message_return_payload(),
    )


def get_telemetry() -> None:
    connect_client_loop(
        connect_callback=on_connect(topic="v1/devices/me/telemetry"),
        message_callback=on_message_return_payload(),
    )


def get_instance(instance_id: str) -> None:
    connect_client_loop(
        connect_callback=on_connect(topic="v1/devices/me/attributes"),
        message_callback=on_message_instance(instance_id),
    )


def get(**kwargs: dict) -> None:
    if kwargs["get_action"] == GetObjects.DEPLOYMENT:
        get_deployment()
    if kwargs["get_action"] == GetObjects.TELEMETRY:
        get_telemetry()
    if kwargs["get_action"] == GetObjects.INSTANCE:
        get_instance(kwargs["instance_id"])
