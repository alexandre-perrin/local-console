from wedge_cli.clients.agent import Agent


def logs(**kwargs: dict) -> None:
    agent = Agent()
    agent.publish_logs(kwargs["instance_id"][0])
    agent.get_logs(kwargs["instance_id"][0], kwargs["timeout"])  # type: ignore
