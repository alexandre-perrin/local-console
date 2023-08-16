import paho.mqtt.client as mqtt
from argparse import Namespace
from wedge_cli.utils.enums import GetObjects
import json
import logging

logger = logging.getLogger(__name__)
def on_connect(topic):
    def callback(client, userdata, flags, rc,):
        client.subscribe(topic)
    return callback
def on_message_return_payload():
    def callback(client, userdata, msg):
        payload = json.loads(msg.payload)
        logger.info(payload)
    return callback

def on_message_instance(instance_id):
    def callback(client, userdata, msg):
        instances = json.loads(msg.payload)["deploymentStatus"]["instances"]
        for instance in list(instances.keys()):
            if instance==instance_id:
                logger.info(instances[str(instance)])
    return callback

def connect_client_loop(connect_callback, message_callback):
    client = mqtt.Client()
    client.on_connect = connect_callback
    client.on_message = message_callback

    client.connect("localhost", 1883, 60)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        #avoids ugly logs when killing the loop
        pass

def get_deployment():
    connect_client_loop(connect_callback=on_connect(topic="v1/devices/me/attributes"), message_callback=on_message_return_payload())

def get_telemetry():
    connect_client_loop(connect_callback=on_connect(topic="v1/devices/me/telemetry"), message_callback=on_message_return_payload())
def get_instance(instance_id:str):
    connect_client_loop(connect_callback=on_connect(topic="v1/devices/me/attributes"), message_callback=on_message_instance(instance_id))
def get(**kwargs: dict):
    if kwargs["get_action"]==GetObjects.DEPLOYMENT:
        get_deployment()
    if kwargs["get_action"]==GetObjects.TELEMETRY:
        get_telemetry()
    if kwargs["get_action"]==GetObjects.INSTANCE:
        get_instance(kwargs["instance_id"])

