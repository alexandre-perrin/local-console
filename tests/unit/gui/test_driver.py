import importlib
import random
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from local_console.core.config import config_to_schema
from local_console.core.config import get_default_config
from local_console.core.schemas.schemas import AgentConfiguration

# The following lines need to be in this order, in order to
# be able to mock the run_on_ui_thread decorator with
# an identity function
patch(
    "local_console.gui.utils.sync_async.run_on_ui_thread", lambda fn: fn
).start()  # noqa
# TODO: simplify patching
importlib.reload(sys.modules["local_console.gui.driver"])
from local_console.gui.driver import Driver  # noqa


def get_default_config_as_schema() -> AgentConfiguration:
    return config_to_schema(get_default_config())


def create_new(root: Path) -> Path:
    new_file = root / f"{random.randint(1, 1e6)}"
    new_file.write_bytes(b"0")
    return new_file


@pytest.fixture(autouse=True)
def common_patches():
    with (
        patch("local_console.gui.driver.TimeoutBehavior"),
        # This test does not use Hypothesis' strategies as they are not readily
        # integrable with the 'tmpdir' fixture, and anyway the functionality tested
        # by this suite is completely independent on the persistent configuration.
        patch("local_console.gui.driver.get_config", get_default_config_as_schema),
        patch("local_console.clients.agent.get_config", get_default_config_as_schema),
    ):
        yield


def test_file_move(tmpdir):
    origin = Path(tmpdir.join("fileA"))
    origin.write_bytes(b"0")

    target = Path(tmpdir.mkdir("sub").mkdir("subsub"))
    moved = Path(shutil.move(origin, target))
    assert moved.parent == target


def test_storage_paths(tmpdir):
    tgd = Path(tmpdir.mkdir("images"))
    driver = Driver(MagicMock())

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


def test_save_into_image_directory(tmpdir):
    root = Path(tmpdir)
    tgd = root / "notexists"

    driver = Driver(MagicMock())

    assert not tgd.exists()
    driver.temporary_image_directory = tgd
    driver.set_image_directory(tgd)
    assert tgd.exists()

    tgd.rmdir()

    assert not tgd.exists()
    driver.save_into_image_directory(create_new(root))
    assert tgd.exists()


def test_save_into_inferences_directory(tmpdir):
    root = Path(tmpdir)
    tgd = root / "notexists"

    driver = Driver(MagicMock())

    assert not tgd.exists()
    driver.temporary_inference_directory = tgd
    driver.set_inference_directory(tgd)
    assert tgd.exists()

    tgd.rmdir()

    assert not tgd.exists()
    driver.save_into_inferences_directory(create_new(root))
    assert tgd.exists()


def test_process_camera_upload_images(tmpdir):
    root = Path(tmpdir)

    with (
        patch.object(
            Driver, "save_into_image_directory"
        ) as mock_save_into_image_directory,
        patch.object(Driver, "update_images_display") as mock_update_images_display,
    ):
        driver = Driver(MagicMock())
        file = root / "images/a.png"
        driver.process_camera_upload(file)
        mock_save_into_image_directory.assert_called_once_with(file)
        mock_update_images_display.assert_called_once_with(
            mock_save_into_image_directory.return_value
        )


def test_process_camera_upload_inferences(tmpdir):
    root = Path(tmpdir)

    with (
        patch.object(
            Driver, "save_into_inferences_directory"
        ) as mock_save_into_inferences_directory,
        patch.object(Driver, "update_inference_data") as mock_update_inference_data,
        patch.object(
            Driver, "update_inference_data_flatbuffers"
        ) as mock_update_inference_data_flatbuffers,
    ):
        driver = Driver(MagicMock())
        file = root / "inferences/a.png"
        driver.process_camera_upload(file)
        mock_save_into_inferences_directory.assert_called_once_with(file)
        mock_update_inference_data.assert_called_once_with(
            mock_save_into_inferences_directory.return_value.read_text.return_value
        )
        mock_update_inference_data_flatbuffers.assert_not_called()


def test_process_camera_upload_inferences_with_fb(tmpdir):
    root = Path(tmpdir)

    with (
        patch.object(
            Driver, "save_into_inferences_directory"
        ) as mock_save_into_inferences_directory,
        patch.object(Driver, "update_inference_data") as mock_update_inference_data,
        patch.object(
            Driver, "update_inference_data_flatbuffers"
        ) as mock_update_inference_data_flatbuffers,
    ):
        driver = Driver(MagicMock())
        driver.flatbuffers_schema = Path(".")
        file = root / "inferences/a.png"
        driver.process_camera_upload(file)
        mock_save_into_inferences_directory.assert_called_once_with(file)
        mock_update_inference_data.assert_not_called()
        mock_update_inference_data_flatbuffers.assert_called_once_with(
            mock_save_into_inferences_directory.return_value
        )
