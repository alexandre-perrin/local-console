from typing import Annotated

import typer
from wedge_cli.clients.agent import Agent

app = typer.Typer(
    help="Command for getting logs reported by a specific module instance"
)


@app.callback(invoke_without_command=True)
def logs(
    instance_id: Annotated[
        str,
        typer.Argument(help="ID of the instance to get the logs from"),
    ],
    timeout: Annotated[
        int,
        typer.Option(
            "-t",
            "--timeout",
            help="Max time to wait for a module instance log to be reported",
        ),
    ] = 10,
) -> None:
    agent = Agent()  # type: ignore
    try:
        agent.rpc(instance_id, "$agent/set", '{"log_enable": true}')
        agent.get_logs(instance_id, timeout)
    except ConnectionError:
        exit(1)
