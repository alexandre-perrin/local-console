import logging

from wedge_cli.clients.agent import Agent


logger = logging.getLogger(__name__)


def rpc(**kwargs: dict) -> None:
    agent = Agent()
    instance_id: str = kwargs["instance_id"][0]
    method: str = kwargs["method"][0]
    params: str = kwargs["params"][0]
    agent.rpc(instance_id, method, params)
