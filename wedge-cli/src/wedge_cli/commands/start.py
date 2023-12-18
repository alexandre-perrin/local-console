import logging
import os
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


def start_agent(connection_info: RemoteConnectionInfo, libraries: Libraries) -> None:
    if not None in connection_info.__dict__.values():
        server = Listener(
            ip=connection_info.host, port=connection_info.port  # type:ignore
        )
        server.open_listener()
        server.receive_config()

    try:
        # this will be avoided when all the commands are done
        config: AgentConfiguration = get_config()
        env = os.environ.copy()
        env[EVPEnvVars.EVP_IOT_PLATFORM] = config.evp.iot_platform
        env[EVPEnvVars.EVP_MQTT_HOST] = config.mqtt.host.ip_value
        env[EVPEnvVars.EVP_MQTT_PORT] = str(config.mqtt.port)
        env[EVPEnvVars.EVP_DATA_DIR] = str(config_paths.evp_data_path)  # type:ignore
        env[EVPEnvVars.EVP_MQTT_CLIENTID] = str(config.mqtt.device_id)
        env[EVPEnvVars.EVP_HTTPS_CA_CERT] = str(
            config_paths.https_ca_path
        )  # type:ignore
        env[EVPEnvVars.EVP_REPORT_STATUS_INTERVAL_MAX_SEC] = "3"
        # TODO: check process return code
        command = [Commands.EVP_AGENT.value]
        if libraries.libraries:
            libraries_command = []
            for l in libraries.libraries:
                libraries_command.append("-l")
                libraries_command.append(l)  # type:ignore
            command += libraries_command  # type: ignore
        logger.debug(f"Running: {' '.join(command)}")
        run(command, env=env)
    except FileNotFoundError:
        logger.warning("evp_agent not in PATH")
        exit(1)


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
        start_agent(
            connection_info=RemoteConnectionInfo(host=ip_value, port=remote[1]),  # type: ignore
            libraries=Libraries(libraries=libraries),  # type: ignore
        )  # type:ignore
    except ValidationError as e:
        logger.warning(
            f"Error with parameter {e.errors()[0]['loc'][0]}. {e.errors()[0]['msg']}"
        )
