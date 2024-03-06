import json
import logging
from collections import defaultdict
from typing import Annotated
from typing import Callable

import trio
import typer
from wedge_cli.clients.agent import Agent
from wedge_cli.core.camera import MQTTTopics

logger = logging.getLogger(__name__)

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
        agent.read_only_loop(
            subs_topics=[MQTTTopics.TELEMETRY.value],
            message_task=on_message_logs(instance_id, timeout),
        )
    except ConnectionError:
        raise SystemExit(
            f"Could not send command for enabling logs to device {instance_id}"
        )


def on_message_logs(instance_id: str, timeout: int) -> Callable:
    async def __task(cs: trio.CancelScope, agent: Agent) -> None:
        assert agent.client is not None
        with trio.move_on_after(timeout) as time_cs:
            async with agent.client.messages() as mgen:
                async for msg in mgen:
                    payload = json.loads(msg.payload.decode())
                    logs = defaultdict(list)
                    if "values" in payload:
                        payload = payload["values"]
                    if "device/log" in payload.keys():
                        for log in payload["device/log"]:
                            logs[log["app"]].append(log)
                        if instance_id in logs.keys():
                            time_cs.deadline += timeout
                            for instance_log in logs[instance_id]:
                                print(instance_log)

        if time_cs.cancelled_caught:
            logger.error(
                f"No logs received for {instance_id} within {timeout} seconds. Please check the instance id is correct"
            )
            cs.cancel()

    return __task
