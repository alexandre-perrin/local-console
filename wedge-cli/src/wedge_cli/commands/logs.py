from wedge_cli.clients.agent import agent


def logs(**kwargs: dict) -> None:
    agent.publish_logs(kwargs["instance_id"][0])
    agent.get_logs(kwargs["instance_id"][0], kwargs["timeout"])  # type: ignore
