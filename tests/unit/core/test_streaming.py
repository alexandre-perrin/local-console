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
from pathlib import Path

import pytest
from local_console.core.camera.streaming import FileGrouping
from local_console.core.camera.streaming import FileGroupingError


def test_file_grouping():
    """
    Test how image and inference file data is assembled into groups,
    as the files come from the camera over the web server.
    """
    expected_extensions = {"jpg", "txt"}
    fg = FileGrouping(expected_extensions)

    # Start assembling a group
    fg.register(Path("inferences/0.txt"), 1)

    # There is no group ready yet!
    with pytest.raises(StopIteration):
        next(fg)

    fg.register(Path("images/0.jpg"), 1)
    # Group is complete, retrieve it
    assert next(fg) == {"jpg": 1, "txt": 1}

    # There are no new groups
    with pytest.raises(StopIteration):
        next(fg)

    # Check ordering of iterating over the grouper
    # It should behave as a FIFO.
    n_elems = 5
    for index in range(n_elems):
        for ext in expected_extensions:
            fg.register(Path(f"{index}.{ext}"), index)

    gather = [g["txt"] for g in fg]
    assert gather == list(range(n_elems))


def test_file_grouping_unknown_parent():
    expected_extensions = {"jpg", "txt"}
    fg = FileGrouping(expected_extensions)

    with pytest.raises(FileGroupingError):
        fg.register(Path("videos/somename.mkv"), None)
