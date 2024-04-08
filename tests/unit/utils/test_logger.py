from collections.abc import Iterator
from contextlib import contextmanager
from unittest.mock import MagicMock
from unittest.mock import patch

from wedge_cli.utils.logger import configure_logger
from wedge_cli.utils.logger import LOG_FORMAT


@contextmanager
def mock_logging() -> Iterator[MagicMock]:
    with patch("wedge_cli.utils.logger.logging") as mock_logging:
        yield mock_logging


def test_configure_logger():
    with mock_logging() as mock_log:
        configure_logger(False, False)
        mock_log.basicConfig.assert_called_once_with(
            format=LOG_FORMAT, level=mock_log.INFO
        )


def test_configure_logger_silent():
    with mock_logging() as mock_log:
        configure_logger(True, False)
        mock_log.basicConfig.assert_called_once_with(
            format=LOG_FORMAT, level=mock_log.WARNING
        )


def test_configure_logger_verbose():
    with mock_logging() as mock_log:
        configure_logger(False, True)
        mock_log.basicConfig.assert_called_once_with(
            format=LOG_FORMAT, level=mock_log.DEBUG
        )


def test_configure_logger_silent_verbose():
    with mock_logging() as mock_log:
        configure_logger(True, True)
        mock_log.basicConfig.assert_called_once_with(
            format=LOG_FORMAT, level=mock_log.WARNING
        )
