from typing import Annotated

import trio
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
            help="Max seconds to wait for a module instance log to be reported",
        ),
    ] = 10,
) -> None:
    agent = Agent()  # type: ignore
    try:
        trio.run(agent.request_instance_logs, instance_id)
        agent.get_instance_logs(instance_id, timeout)
    except ConnectionError:
        raise SystemExit(
            f"Could not send command for enabling logs to device {instance_id}"
        )
