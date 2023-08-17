import argparse
import re
import textwrap


def regex_entry(
    arg_value: str, pat: re.Pattern = re.compile(r"^[\w-]+\.[\w-]+=[\w-]+$")
) -> str:
    if not pat.match(arg_value):
        raise argparse.ArgumentTypeError(
            "Invalid value. Use format <section>.<item>=<value>"
        )
    return arg_value


def get_parser() -> argparse.ArgumentParser:
    """Get CLI parser arguments."""
    parser = argparse.ArgumentParser(description="Wedge-Agent CLI")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-d", "--debug", action="store_true")
    # Commands
    command = parser.add_subparsers(dest="command")
    # Command: start
    start = command.add_parser("start", description="Start the agent")  # noqa: F841
    # Command: deploy
    deploy = command.add_parser(  # noqa: F841
        "deploy", description="Deploy application of current working directory"
    )
    deploy.add_argument(
        "-e", "--empty", action="store_true", help="Deploy empty application"
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
                    Runtime option used by the devic to determine the EVP protocol to be used with the EVP hub.
                    Accepted values are EVP1 and EVP2.
                    By default is EVP2.

            mqtt.host
                    URL used to connect to the mqtt broker. By default is localhost.

            mqtt.port
                    Port number used to connect to the mqtt broker. By default is 1883.
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
        help="key to set. Format <section>.<option>=<value>. E.g., mqtt.port=1234",
    )

    # Command: log
    logs = command.add_parser("logs", description="Get logs of a specific instance")
    logs.add_argument("instance_id", nargs=1)

    return parser
