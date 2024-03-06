import logging


def configure_logger(silent: bool, verbose: bool) -> None:
    level = logging.INFO
    if verbose:
        level = logging.DEBUG
    if silent:
        level = logging.WARNING
    logging.basicConfig(format="%(levelname)s: %(message)s", level=level)
