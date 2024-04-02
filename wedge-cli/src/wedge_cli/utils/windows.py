import ctypes
import sys
from ctypes import wintypes

# Constants for "Program Files" folder, using CSIDL value
CSIDL_PROGRAM_FILES = 38  # For the Program Files folder


def get_program_files_path() -> str:
    if sys.platform == "win32":
        # Buffer size (MAX_PATH)
        buffer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        # Call to SHGetFolderPath
        ctypes.windll.shell32.SHGetFolderPathW(0, CSIDL_PROGRAM_FILES, 0, 0, buffer)

        return buffer.value
    else:
        return ""
