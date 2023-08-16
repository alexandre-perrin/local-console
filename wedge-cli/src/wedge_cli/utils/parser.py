import argparse


def get_parser() -> argparse.ArgumentParser:
    """Get CLI parser arguments."""
    parser = argparse.ArgumentParser(description="Wedge-Agent CLI")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-d", "--debug", action="store_true")
    # Commands
    command = parser.add_subparsers(dest="command")
    # Command: start
    start = command.add_parser("start", description="Start the agent")  # noqa: F841
    # Command: get
    get = command.add_parser("get", description="Get status, telemetries or logs")
    get_subparsers = get.add_subparsers()
    get_deployment = get_subparsers.add_parser(  # noqa: F841
        "deployment", description="Get the status of deployment"
    )
    get_telemetry = get_subparsers.add_parser(  # noqa: F841
        "telemetry", description="Get the telemetries"
    )
    get_instance = get_subparsers.add_parser(  # noqa: F841
        "instance", description="Get the status of instance"
    )
    return parser
