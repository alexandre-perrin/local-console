import argparse
import re


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
    get_subparsers = get.add_subparsers(dest="get_subparsers")
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
    config = command.add_parser(  # noqa: F841
        "config", description="Get and modify configuration"
    )
    config_subparsers = config.add_subparsers(dest="config_subparsers", required=True)
    config_get = config_subparsers.add_parser(  # noqa: F841
        "get", description="Get configuration"
    )
    config_get.add_argument("key", nargs="?", help="Optional key to get")
    config_set = config_subparsers.add_parser(  # noqa: F841
        "set", description="Set configuration"
    )
    config_set.add_argument(
        "entry",
        nargs=1,
        type=regex_entry,
        help="key to set. Format <section>.<option>=<value>. E.g., mqtt.port=1234",
    )
    return parser
