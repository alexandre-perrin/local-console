from unittest.mock import MagicMock
from unittest.mock import patch

from wedge_cli.utils.windows import get_program_files_path


def test_get_program_files_path_linux():
    with patch("wedge_cli.utils.windows.sys") as mock_sys:
        mock_sys.platform = "linux"
        assert get_program_files_path() == ""


def test_get_program_files_path_windows():
    CSIDL_PROGRAM_FILES = 38
    expected_path = "C:\\Program Files"

    with (
        patch("wedge_cli.utils.windows.sys") as mock_sys,
        patch("wedge_cli.utils.windows.ctypes") as mock_ctypes,
        patch("wedge_cli.utils.windows.wintypes") as mock_wintypes,
    ):
        mock_sys.platform = "win32"
        mock_buffer = MagicMock()
        mock_ctypes.create_unicode_buffer.return_value = mock_buffer
        mock_ctypes.windll.shell32.SHGetFolderPathW.return_value = 0  # Simulate success
        mock_buffer.value = expected_path

        assert get_program_files_path() == expected_path

        mock_ctypes.create_unicode_buffer.assert_called_once_with(
            mock_wintypes.MAX_PATH
        )
        mock_ctypes.windll.shell32.SHGetFolderPathW.assert_called_once_with(
            0, CSIDL_PROGRAM_FILES, 0, 0, mock_buffer
        )
        assert isinstance(get_program_files_path(), str)
        assert get_program_files_path() == expected_path
