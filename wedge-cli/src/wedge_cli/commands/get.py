from typing import Annotated

import typer
from wedge_cli.clients.agent import Agent

app = typer.Typer(
    name="get", help="Command to get information of the running sensing application"
)


@app.command(help="Get the status of deployment")
def deployment() -> None:
    agent = Agent()
    agent.get_deployment()


@app.command(help="Get the telemetries")
def telemetry() -> None:
    agent = Agent()
    agent.get_telemetry()


@app.command(help="Get the status of instance")
def instance(
    instance_id: Annotated[
        str,
        typer.Argument(help="Target instance of the RPC."),
    ]
) -> None:
    agent = Agent()
    agent.get_instance(instance_id)
