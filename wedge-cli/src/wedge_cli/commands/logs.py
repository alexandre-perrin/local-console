from wedge_cli.clients.agent import Agent


def logs(**kwargs: dict) -> None:
    agent = Agent()
    instance_id: str = kwargs["instance_id"][0]
    agent.publish_logs(instance_id)
    timeout = int(kwargs["timeout"])  # type: ignore
    agent.get_logs(instance_id, timeout)
