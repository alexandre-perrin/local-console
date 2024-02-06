import logging
import os
import shutil
from subprocess import run
from typing import Annotated
from typing import Optional

import typer
from pydantic import ValidationError
from wedge_cli.clients.listener import Listener
from wedge_cli.utils.config import get_config
from wedge_cli.utils.enums import Commands
from wedge_cli.utils.enums import config_paths
from wedge_cli.utils.enums import EVPEnvVars
from wedge_cli.utils.schemas import AgentConfiguration
from wedge_cli.utils.schemas import IPAddress
from wedge_cli.utils.schemas import Libraries
from wedge_cli.utils.schemas import RemoteConnectionInfo

logger = logging.getLogger(__name__)
app = typer.Typer(help="Command that starts the agent up")


def start_agent(connection_info: RemoteConnectionInfo, libraries: Libraries) -> int:
    if not None in connection_info.__dict__.values():
        server = Listener(
            ip=connection_info.host, port=connection_info.port  # type:ignore
        )
        server.open_listener()
        server.receive_config()

    retcode = 1
    try:
        config: AgentConfiguration = get_config()
        agent_env = get_agent_environment(config)
        agent_command = get_agent_command_parts(libraries)
        logger.debug(f"Running: {' '.join(agent_command)}")
        run(agent_command, env=agent_env, check=True)
        retcode = 0
    except FileNotFoundError:
        logger.error("evp_agent not in PATH")
    except ConnectionError as e:
        logger.error(f"Connection error: {e}")
    except KeyboardInterrupt:
        logger.debug("Terminated by SIGTERM")
        retcode = 0
    except SystemExit:
        logger.debug("Terminated by SIGINT")
        retcode = 0

    return retcode


def get_agent_command_parts(libraries: Libraries) -> list[str]:
    agent_path = shutil.which(Commands.EVP_AGENT.value)
    if not agent_path:
        raise FileNotFoundError("evp_agent not in PATH")

    command = [
        str(agent_path),
    ]

    if libraries.libraries:
        for l in libraries.libraries:
            command.append("-l")
            command.append(l)  # type:ignore

    return command


def get_agent_environment(config: AgentConfiguration) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            EVPEnvVars.EVP_IOT_PLATFORM: config.evp.iot_platform,
            EVPEnvVars.EVP_MQTT_HOST: config.mqtt.host.ip_value,
            EVPEnvVars.EVP_MQTT_PORT: str(config.mqtt.port),
            EVPEnvVars.EVP_DATA_DIR: str(config_paths.evp_data_path),  # type:ignore
            EVPEnvVars.EVP_HTTPS_CA_CERT: str(
                config_paths.https_ca_path
            ),  # type:ignore
            EVPEnvVars.EVP_REPORT_STATUS_INTERVAL_MAX_SEC: "3",
        }
    )
    device_id: Optional[str] = config.mqtt.device_id
    env[EVPEnvVars.EVP_MQTT_CLIENTID] = (
        device_id if device_id else get_random_identifier("agent-", 7)
    )

    return env


@app.callback(invoke_without_command=True)
def start(
    remote: Annotated[
        tuple[str, int],
        typer.Option(
            help="Start the agent waiting for the configuration to be sent. Need to specify host and port: "
            "e.g. --remote localhost 8001"
        ),
    ] = (  # type: ignore
        None,
        None,
    ),
    libraries: Annotated[
        Optional[list[str]],
        typer.Option(
            "--library",
            "-l",
            help="Library to be loaded by the agent ",
        ),
    ] = [],
) -> None:
    if remote[0]:
        try:
            ip_value = IPAddress(ip_value=remote[0])
        except ValueError:
            logger.warning(f"Invalid host {remote[0]}. Send a valid ip")
            exit(1)
    else:
        ip_value = None
    try:
        rc = start_agent(
            connection_info=RemoteConnectionInfo(host=ip_value, port=remote[1]),  # type: ignore
            libraries=Libraries(libraries=libraries),  # type: ignore
        )  # type:ignore
        exit(rc)
    except ValidationError as e:
        logger.warning(
            f"Error with parameter {e.errors()[0]['loc'][0]}. {e.errors()[0]['msg']}"
        )


def get_random_identifier(prefix: str = "", max_length: int = 36) -> str:
    random_serial = int.from_bytes(os.urandom(20), "big") >> 1
    full = prefix + str(random_serial)
    return full[:max_length]
