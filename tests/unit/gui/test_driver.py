import random
import shutil
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

from wedge_cli.core.config import config_to_schema
from wedge_cli.core.config import get_default_config
from wedge_cli.core.schemas.schemas import AgentConfiguration

# The following lines need to be in this order, in order to
# be able to mock the run_on_ui_thread decorator with
# an identity function
patch("wedge_cli.gui.utils.sync_async.run_on_ui_thread", lambda fn: fn).start()  # noqa
from wedge_cli.gui.driver import Driver  # noqa


def test_file_move(tmpdir):
    origin = Path(tmpdir.join("fileA"))
    origin.write_bytes(b"0")

    target = Path(tmpdir.mkdir("sub").mkdir("subsub"))
    moved = Path(shutil.move(origin, target))
    assert moved.parent == target


def create_new(root: Path) -> Path:
    new_file = root / f"{random.randint(1, 1e6)}"
    new_file.write_bytes(b"0")
    return new_file


def get_default_config_as_schema() -> AgentConfiguration:
    return config_to_schema(get_default_config())


def test_storage_paths(tmpdir):
    tgd = Path(tmpdir.mkdir("images"))

    with (
        patch("wedge_cli.gui.driver.TimeoutBehavior"),
        # This test does not use Hypothesis' strategies as they are not readily
        # integrable with the 'tmpdir' fixture, and anyway the functionality tested
        # by this suite is completely independent on the persistent configuration.
        patch("wedge_cli.gui.driver.get_config", get_default_config_as_schema),
        patch("wedge_cli.clients.agent.get_config", get_default_config_as_schema),
    ):
        mock_gui = MagicMock()
        mock_nursery = MagicMock()
        driver = Driver(mock_gui, mock_nursery)

        # Set default image dir
        driver.temporary_image_directory = tgd
        driver.set_image_directory(tgd)

        # Storing an image when image dir has not changed default
        new_image = create_new(tgd)
        saved = driver.save_into_image_directory(new_image)
        assert saved.parent == tgd

        # Change the target image dir
        new_image_dir = Path(tmpdir.mkdir("another_image_dir"))
        driver.set_image_directory(new_image_dir)

        # Storing an image when image dir has been changed
        new_image = create_new(tgd)
        saved = driver.save_into_image_directory(new_image)
        assert saved.parent == new_image_dir
