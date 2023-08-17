from wedge_cli.clients.agent import agent
from wedge_cli.utils.enums import GetObjects

GET_COMMANDS = {
    GetObjects.DEPLOYMENT: agent.get_deployment,
    GetObjects.TELEMETRY: agent.get_telemetry,
    GetObjects.INSTANCE: agent.get_instance,
}


def get(**kwargs: dict) -> None:
    GET_COMMANDS[GetObjects(kwargs["get_subparsers"])](**kwargs)
