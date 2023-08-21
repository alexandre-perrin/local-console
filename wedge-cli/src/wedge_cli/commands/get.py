from wedge_cli.clients.agent import Agent
from wedge_cli.utils.enums import GetObjects


def get(**kwargs: dict) -> None:
    agent = Agent()
    get_command = {
        GetObjects.DEPLOYMENT: agent.get_deployment,
        GetObjects.TELEMETRY: agent.get_telemetry,
        GetObjects.INSTANCE: agent.get_instance,
    }
    get_command[GetObjects(kwargs["get_subparsers"])](**kwargs)
