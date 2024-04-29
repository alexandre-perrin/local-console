from pathlib import Path
from unittest.mock import patch

import local_console.gui.config as config
from local_console.gui.config import CONFIG_PATH
from local_console.gui.config import configure
from local_console.gui.config import resource_path


def test_configure():
    with patch("local_console.gui.config.Config.read") as mock_read:
        configure()
        mock_read.assert_called_once_with(CONFIG_PATH)


def test_configure_file_no_exists():
    with (
        patch("local_console.gui.config.Path.is_file") as mock_is_file,
        patch("local_console.gui.config.Config.read") as mock_read,
    ):
        mock_is_file.return_value = False
        configure()
        mock_read.assert_not_called()


def test_resource_path():
    assert resource_path("assets/config.ini") == str(
        Path(config.__file__).parent / "assets/config.ini"
    )
    assert resource_path("config.py") == str(Path(config.__file__).parent / "config.py")
    assert resource_path("wrong_file.txt") is None
