import json
import logging
import socket
from pathlib import Path
from typing import Annotated
from typing import Optional

import typer
from wedge_cli.utils.config import check_section_and_params
from wedge_cli.utils.config import get_config
from wedge_cli.utils.config import parse_section_to_ini
from wedge_cli.utils.config import schema_to_parser
from wedge_cli.utils.enums import config_paths
from wedge_cli.utils.schemas import AgentConfiguration
from wedge_cli.utils.schemas import IPAddress
from wedge_cli.utils.schemas import RemoteConnectionInfo

logger = logging.getLogger(__name__)
app = typer.Typer(help="Commands that interact with the configuration of the agent")


def send_config(config_dict: dict, connection_info: RemoteConnectionInfo) -> None:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((connection_info.host.ip_value, connection_info.port))  # type: ignore
    s.send(bytes(json.dumps(config_dict), "utf-8"))

    while True:
        reply = s.recv(1024)
        if not reply:
            continue
        elif reply:
            logger.info(reply.decode("utf-8"))
            break


@app.command("get", help="Gets the config key values requested or the whole config")
def config_get(
    section: Annotated[
        Optional[str],
        typer.Argument(
            help="Section to be retrieved if none is specified returns the whole config"
        ),
    ] = None,
    parameter: Annotated[
        Optional[str],
        typer.Argument(
            help="Parameter from a specific section to be retrieved if none is specified returns the whole section"
        ),
    ] = None,
) -> None:
    agent_config: AgentConfiguration = get_config()  # type: ignore
    if section is None:
        for section_name, section_value in agent_config.__dict__.items():
            parsed_section = parse_section_to_ini(section_value, section_name)
            print(parsed_section, "\n")
    else:
        try:
            check_section_and_params(agent_config, section, parameter)
        except ValueError:
            exit(1)
        parsed_section = parse_section_to_ini(
            agent_config.__dict__[f"{section}"], section, parameter
        )
        print(parsed_section)


@app.command("set", help="Sets the config key values to the specified value")
def config_set(
    section: Annotated[
        str,
        typer.Argument(help="Section of the configuration to be set"),
    ],
    parameter: Annotated[
        str,
        typer.Argument(help="Parameter of the section of the configuration to be set"),
    ],
    new: Annotated[
        str,
        typer.Argument(
            help="New value to be used in the specified parameter of the section"
        ),
    ],
) -> None:
    agent_config: AgentConfiguration = get_config()  # type:ignore

    try:
        check_section_and_params(agent_config, section, parameter)
        config_parser = schema_to_parser(agent_config, section, parameter, new)
    except ValueError:
        exit(1)

    with open(
        config_paths.config_path, "w"  # type:ignore
    ) as f:
        config_parser.write(f)


@app.command(
    "send", help="Send the configuration to an agent started with the remote option"
)
def config_send(
    config_file: Annotated[
        Path,
        typer.Option(
            help="Path to a .ini file where the configuration to be sent is defined, it should have the same format as the on in ~/.config/wedge."
        ),
    ],
    ip: Annotated[str, typer.Option(help="IP where the configuration is send")],
    port: Annotated[int, typer.Option(help="Port where the configuration is send")],
) -> None:
    if config_file.suffix != ".ini":
        logger.error("Specified file is not a .ini file")
        exit(1)

    else:
        try:
            connection_info = RemoteConnectionInfo(
                host=IPAddress(ip_value=ip), port=port
            )
        except ValueError:
            logger.warning("Invalid IP address used")
            exit(1)

        agent_config: AgentConfiguration = get_config(config_file)
        config_dict: dict = agent_config.model_dump()
        send_config(config_dict, connection_info)
