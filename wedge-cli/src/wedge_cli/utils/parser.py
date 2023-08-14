import argparse


def get_parser() -> argparse.Namespace:
    """Get CLI parser arguments."""
    parser = argparse.ArgumentParser(description="Wedge-Agent CLI")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-d", "--debug", action="store_true")
    subparsers = parser.add_subparsers(help="sub-command help", dest="subparser_name")
    deploy = subparsers.add_parser("deploy", description="")
    deploy.add_argument(
        "--placeholder",
        type=str,
        required=True,
        help="",
    )
    get = subparsers.add_parser("get", description="")
    get.add_argument(
        "--telemetry",
        type=str,
        required=True,
        help="",
    )
    return parser.parse_args()
