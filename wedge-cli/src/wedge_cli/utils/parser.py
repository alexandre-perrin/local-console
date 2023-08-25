import argparse
import re
import textwrap

from wedge_cli.utils.enums import Target


def regex_entry(
    arg_value: str, pat: re.Pattern = re.compile(r"^[\w-]+\.[\w-]+=[\.\w-]+$")
) -> str:
    if not pat.match(arg_value):
        raise argparse.ArgumentTypeError(
            "Invalid value. Use format <section>.<item>=<value>"
        )
    return arg_value


def ip_entry(
    arg_value: str,
    pat: re.Pattern = re.compile(
        r"^(localhost|((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4})$"
    ),
) -> str:
    if not pat.match(arg_value):
        raise argparse.ArgumentTypeError("Invalid value. Use format of an IP address")
    return arg_value


def get_parser() -> argparse.ArgumentParser:
    """Get CLI parser arguments."""
    parser = argparse.ArgumentParser(description="Wedge-Agent CLI")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-d", "--debug", action="store_true")
    parser.add_argument(
        "-D",
        "--config_dir",
        type=str,
        default=".config/wedge",
        help="Directory to save the wedge agent information. Defaults to '~/.config/wedge/'",
    )
    # Commands
    command = parser.add_subparsers(dest="command")
    # Command: start
    start = command.add_parser("start", description="Start the agent")  # noqa: F841
    start.add_argument(
        "-l",
        "--library",
        nargs="*",
        type=str,
        help="Native libraries (capabilities). They must be accessible from LD_LIBRARY_PATH",
    )
    start.add_argument(
        "--remote",
        action="store_true",
        help="Enable remote starting, which waits for the configuration to arrive and starts the agent",
    )
    start_remote = start.add_argument_group(
        "remote",
    )
    start_remote.add_argument(
        "-i",
        "--ip",
        type=ip_entry,
        help="IP to show for receiving the configuration. Only meaningful when used with --remote",
    )
    start_remote.add_argument(
        "-p",
        "--port",
        type=int,
        help="Port to show for receiving the configuration. Only meaningful when used with --remote",
    )
    # Command: deploy
    deploy = command.add_parser(  # noqa: F841
        "deploy", description="Deploy application of current working directory"
    )
    deploy.add_argument(
        "-e", "--empty", action="store_true", help="Deploy empty application"
    )
    deploy.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=10,
        help="Seconds for the webserver to wait that the agent downloads the modules",
    )
    # Command: build
    build = command.add_parser(  # noqa: F841
        "build", description="Build application of current working directory"
    )
    build.add_argument("target", nargs="?", type=Target, choices=list(Target))
    # Command: new
    new = command.add_parser(  # noqa: F841
        "new", description="Create a new template application"
    )
    new.add_argument(
        "project_name",
        nargs=1,
        help="Folder name to create new project",
    )
    # Command: get
    get = command.add_parser("get", description="Get status, telemetries or logs")
    get_subparsers = get.add_subparsers(dest="get_subparsers", required=True)
    get_deployment = get_subparsers.add_parser(  # noqa: F841
        "deployment", description="Get the status of deployment"
    )
    get_telemetry = get_subparsers.add_parser(  # noqa: F841
        "telemetry", description="Get the telemetries"
    )
    get_instance = get_subparsers.add_parser(  # noqa: F841
        "instance", description="Get the status of instance"
    )
    get_instance.add_argument("instance_id", nargs=1)

    # Command: config
    config_description = textwrap.dedent(
        """
        CONFIGURATION ITEMS
            evp.iot-platform
                    Runtime option used by the device to determine the type of IoT Hub used by EVP cloud.
                    Accepted values are tb and c8y. By default is tb.

            evp.version
                    Runtime option used by the device to determine the EVP protocol to be used with the EVP hub.
                    Accepted values are EVP1 and EVP2.
                    By default is EVP2.

            mqtt.host
                    URL used to connect to the mqtt broker. By default is localhost.

            mqtt.port
                    Port number used to connect to the mqtt broker. By default is 1883.

            webserver.host
                    URL used for the agent to download the modules. By default is localhost.

            webserver.port
                    Port number for the agent to download the modules. By default is 8000.
    """
    )
    config = command.add_parser(  # noqa: F841
        "config",
        description=f"Get and modify configuration\n{config_description}",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    config_subparsers = config.add_subparsers(dest="config_subparsers", required=True)
    config_get = config_subparsers.add_parser(  # noqa: F841
        "get",
        description=f"Get configuration\n{config_description}",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    config_get.add_argument("key", nargs="?", help="Optional key to get")
    config_set = config_subparsers.add_parser(  # noqa: F841
        "set",
        description=f"Set configuration\n{config_description}",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    config_set.add_argument(
        "entry",
        nargs=1,
        type=regex_entry,
        help="key to set. Format <section>.<option>=<value>. For example, mqtt.port=1234",
    )
    config_send = config_subparsers.add_parser(  # noqa: F841
        "send",
        description=f"Send configuration to specified IP and port\n{config_description}",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    config_send.add_argument(
        "--ip",
        required=True,
        type=ip_entry,
        help="IP address of the remote device",
    )
    config_send.add_argument(
        "--port",
        required=True,
        help="Port number of the remote device",
    )
    config_send.add_argument(
        "entries",
        nargs="*",
        type=regex_entry,
        help="key to set. Format <section>.<option>=<value>. E.g., mqtt.port=1234",
    )
    # Command: log
    logs = command.add_parser("logs", description="Get logs of a specific instance")
    logs.add_argument("instance_id", nargs=1)
    logs.add_argument(
        "timeout",
        nargs="?",
        type=int,
        default=5,
        help="Max time to wait for a module instance log to be reported",
    )
    # Command: rpc
    rpc_description = textwrap.dedent(
        """
        Send RPC to module instance

        Examples
            Set color to yellow in rpc-example
                wedge-cli rpc node my-method '{"rgb":"FFFF00"}'
    """
    )
    rpc = command.add_parser(
        "rpc",
        description=rpc_description,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    rpc.add_argument("instance_id", nargs=1, help="Target instance of the RPC.")
    rpc.add_argument("method", nargs=1, help="Method of the RPC.")
    rpc.add_argument("params", nargs=1, help="JSON representing the parameters.")
    return parser
