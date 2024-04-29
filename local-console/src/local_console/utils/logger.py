import logging

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s"


def configure_logger(silent: bool, verbose: bool) -> None:
    level = logging.INFO
    if verbose:
        level = logging.DEBUG
    if silent:
        level = logging.WARNING
    logging.basicConfig(format=LOG_FORMAT, level=level)
