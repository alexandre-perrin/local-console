import logging


def configure_logger(debug: bool, verbose: bool) -> None:
    level = logging.WARNING
    if verbose:
        level = logging.INFO
    if debug:
        level = logging.DEBUG
    logging.basicConfig(format="%(levelname)s: %(message)s", level=level)
