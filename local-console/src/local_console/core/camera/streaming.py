# Copyright 2024 Sony Semiconductor Solutions Corp.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0
from collections import defaultdict
from collections.abc import Iterator
from pathlib import PurePath
from queue import Empty
from queue import Queue
from typing import Any


FileGroup = dict[str, Any]


class FileGroupingError(Exception):
    """
    Conveys an error when trying to group files
    """


class FileGrouping:
    """
    This class assembles groups of files that have the same
    name stem, and different extensions. For instance, the
    files "1001.jpg" and "1001.txt" form the "1001" file group,
    and their data is accessible via a dictionary whose keys
    are the parent directory names of the corresponding data:
    {
        "1001": {
            "jpg": [...],
            "txt": [...],
        }
    }

    When a group contains a specified set of parent keys,
    it will be available for popping out of the dictionary,
    so that its data gets consumed elsewhere.
    """

    def __init__(self, expected_extensions: set[str]) -> None:
        self.extensions = expected_extensions
        self._groups: dict[str, FileGroup] = defaultdict(dict)
        self._queue: Queue[FileGroup] = Queue()

    def register(self, file_name: PurePath, file_data: Any) -> None:
        """
        Register a file for grouping. Its associated data is arbitrary.
        For instance, it can be a pathlib.Path or a bytes instance.

        Args:
            file_name (PurePath): the file name object
            file_data (Any): data associated to the file
        """
        extension = file_name.suffix.lstrip(".")
        if extension not in self.extensions:
            raise FileGroupingError(f"File {file_name} has unexpected parent")

        stem = file_name.stem
        self._groups[stem][extension] = file_data
        if set(self._groups[stem]) == self.extensions:
            self._queue.put(self._groups.pop(stem))

    def __next__(self) -> FileGroup:
        try:
            return self._queue.get_nowait()
        except Empty:
            raise StopIteration

    def __iter__(self) -> Iterator[FileGroup]:
        while True:
            try:
                yield next(self)
            except StopIteration:
                break
