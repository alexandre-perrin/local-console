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
import contextlib
import logging
import os
import random
import threading
from collections import OrderedDict
from collections.abc import Iterator
from itertools import cycle
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from local_console.utils.fstools import check_and_create_directory
from local_console.utils.fstools import DirectoryMonitor
from local_console.utils.fstools import StorageSizeWatcher
from watchdog.events import FileSystemEvent
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from tests import not_raises

logger = logging.getLogger(__name__)


class FileCreator:
    def __init__(self) -> None:
        self.age = 0

    def __call__(self, path: Path) -> None:
        path.write_bytes(b"0")
        os.utime(path, ns=(self.age, self.age))
        self.age += 1


@pytest.fixture
def file_creator():
    yield FileCreator()


@pytest.fixture
def dir_layout(tmpdir, file_creator):
    entries = [
        tmpdir.join("fileA"),
        tmpdir.join("fileB"),
        tmpdir.mkdir("sub").join("file0"),
        tmpdir.join("sub").mkdir("subsub").join("file0"),
    ]
    # Make all entries, files of size 1
    for e in entries:
        file_creator(Path(e))

    return [Path(tmpdir), len(entries)]


def create_new(root: Path, file_creator) -> Path:
    new_file = root / f"{random.randint(1, int(1e6))}"
    file_creator(new_file)
    return new_file


def test_regular_sequence_base(dir_layout, file_creator):
    dir_base, size = dir_layout
    w = StorageSizeWatcher(check_frequency=10)
    assert w.state == StorageSizeWatcher.State.Start

    w.set_path(dir_base)
    assert w.state == StorageSizeWatcher.State.Accumulating
    assert w.storage_usage == size

    w.incoming(create_new(dir_base, file_creator))
    assert w.state == StorageSizeWatcher.State.Accumulating
    assert w.storage_usage == size + 1
    size += 1

    oldest_age = w.get_oldest().age
    assert oldest_age == 0

    st_limit = 4
    w.set_storage_limit(st_limit)
    oldest_age = w.get_oldest().age
    assert oldest_age == 1
    assert w.storage_usage == st_limit
    assert w._consistency_check()

    # Test creating and registering new files
    # in lockstep
    num_new_files = random.randint(5, 20)
    for _ in range(num_new_files):
        w.incoming(create_new(dir_base, file_creator))
    assert w._consistency_check()
    assert w.storage_usage == st_limit
    expected_oldest_age = oldest_age + num_new_files
    oldest_age = w.get_oldest().age
    # This is due to the timestamp mocking, as each new file
    # is timestamped one time unit later than the previous.
    assert oldest_age == expected_oldest_age

    # Test creating and registering new files
    # not in lockstep
    num_new_files = random.randint(5, 20)
    for _ in range(num_new_files):
        create_new(dir_base, file_creator)
    # although consistency_check restores consistency,
    # it returns whether state was consistent before
    assert not w._consistency_check()
    # hence, a further call should indicate consistency.
    assert w._consistency_check()
    expected_oldest_age = oldest_age + num_new_files

    # However, pruning is still necessary:
    oldest_age = w.get_oldest().age
    assert oldest_age != expected_oldest_age
    assert w.storage_usage != st_limit
    w._prune()
    oldest_age = w.get_oldest().age
    assert oldest_age == expected_oldest_age
    assert w.storage_usage == st_limit


def test_inconsistency_on_unexpected_deletion(dir_layout, caplog, file_creator):
    dir_base, size = dir_layout
    # Have the consistency check executed on the second incoming file
    w = StorageSizeWatcher(check_frequency=2)
    w.set_path(dir_base)

    # Regular update
    to_delete_later = create_new(dir_base, file_creator)
    w.incoming(to_delete_later)

    # Unrecorded update: Previous file is deleted
    to_delete_later.unlink()

    # Regular update
    w.incoming(create_new(dir_base, file_creator))
    assert "File bookkeeping inconsistency: files unexpectedly removed" in caplog.text


def test_ignore_setting_the_same_dir(dir_layout):
    dir_base, size = dir_layout
    w = StorageSizeWatcher(check_frequency=10)
    w._paths = MagicMock()
    w._build_content_list = Mock()

    # First call to set_path works as expected
    w.set_path(dir_base)
    w._paths.add.assert_called_once()
    w._build_content_list.assert_called_once()

    # Second call with the same path, does not increase call count
    w._paths.__contains__.return_value = True
    w.set_path(dir_base)
    w._paths.add.assert_called_once()
    w._build_content_list.assert_called_once()


def test_incoming_always_prunes(dir_layout, file_creator):
    dir_base, size = dir_layout
    mock_prune = Mock()
    with patch.object(StorageSizeWatcher, "_prune", mock_prune):
        w = StorageSizeWatcher(check_frequency=10)
        w.set_path(dir_base)
        st_limit = 4
        assert mock_prune.call_count == 0
        w.set_storage_limit(st_limit)
        assert mock_prune.call_count == 1

        num_new_files = random.randint(5, 20)
        for _ in range(num_new_files):
            w.incoming(create_new(dir_base, file_creator))
        assert mock_prune.call_count == num_new_files + 1


def test_remaining_before_consistency_check(dir_layout, file_creator):
    check_frequency = 10
    storage_limit = 4

    dir_base, size = dir_layout
    mock_prune = Mock()
    with patch.object(StorageSizeWatcher, "_prune", mock_prune):
        w = StorageSizeWatcher(check_frequency=check_frequency)
        w.set_path(dir_base)
        w.set_storage_limit(storage_limit)
        assert w._remaining_before_check == check_frequency

        for i in range(check_frequency):
            assert w._remaining_before_check == check_frequency - i
            w.incoming(create_new(dir_base, file_creator))
        assert w._remaining_before_check == check_frequency


def test_age_bookkeeping():
    names = "abcdefghijklmn"
    timestamps = list(range(len(names)))
    random.shuffle(timestamps)

    # helper dict for building assertions
    min_timestamp = min(timestamps)
    max_timestamp = max(timestamps)
    helper = {
        timestamp: name
        for timestamp, name in zip(timestamps, names)
        if timestamp in (min_timestamp, max_timestamp)
    }
    name_of_min_timestamp = helper[min_timestamp]
    name_of_max_timestamp = helper[max_timestamp]

    odd = OrderedDict(
        sorted(
            ((((timestamp, name), None)) for timestamp, name in zip(timestamps, names)),
            key=lambda e: e[0],
        )
    )
    first_key = next(iter(odd.keys()))
    assert first_key == (min_timestamp, name_of_min_timestamp)

    last_key, _ = odd.popitem()
    assert last_key == (max_timestamp, name_of_max_timestamp)

    popped_first, _ = odd.popitem(last=False)
    assert first_key == popped_first


@pytest.fixture
def multi_dir_layout(tmpdir, file_creator):
    bases = [tmpdir.mkdir("sub_X"), tmpdir.mkdir("sub_Y")]
    entries = [
        bases[0].join("file0"),
        bases[0].mkdir("internal").join("file1"),
        bases[1].join("fileA"),
        bases[1].join("fileB"),
    ]
    # Make all entries, files of size 1
    for e in entries:
        file_creator(Path(e))
    return [Path(b) for b in bases], len(entries)


def test_regular_sequence_multiple_dirs(multi_dir_layout, file_creator):
    dir_bases, initial_size = multi_dir_layout
    expected_curr_size = initial_size

    w = StorageSizeWatcher(check_frequency=10)
    assert w.state == StorageSizeWatcher.State.Start

    w.set_path(dir_bases[0])
    assert w.state == StorageSizeWatcher.State.Accumulating
    assert w.storage_usage < expected_curr_size
    oldest_age = w.get_oldest().age
    assert oldest_age == 0

    w.set_path(dir_bases[1])
    assert w.storage_usage == expected_curr_size
    assert w.state == StorageSizeWatcher.State.Accumulating
    oldest_age = w.get_oldest().age
    assert oldest_age == 0

    # Test that adding a new file while no limit has been set yet,
    # does not invoke pruning, so the previous oldest file remains.
    w.incoming(create_new(dir_bases[0], file_creator))
    expected_curr_size += 1
    assert w.storage_usage == expected_curr_size
    assert w.state == StorageSizeWatcher.State.Accumulating
    oldest_age = w.get_oldest().age
    assert oldest_age == 0

    # Test that setting the size limit, invokes pruning, making
    # the oldest file, a more recent one.
    st_limit = 4
    w.set_storage_limit(st_limit)
    expected_curr_size = st_limit
    assert w.storage_usage == expected_curr_size
    oldest_age = w.get_oldest().age
    assert oldest_age == 1

    # Test creating and registering new files in lockstep
    num_new_files = random.randint(5, 20)
    for _, base in zip(range(num_new_files), cycle(dir_bases)):
        w.incoming(create_new(base, file_creator))
        assert w._consistency_check()
        assert w.storage_usage <= st_limit

    files_created_up_to_now = initial_size + 1 + num_new_files
    expected_newest_age = files_created_up_to_now - 1
    expected_oldest_age = expected_newest_age - st_limit + 1
    oldest_age = w.get_oldest().age
    assert oldest_age == expected_oldest_age

    # Test setting a limit larger than current usage
    st_limit = 7
    w.set_storage_limit(st_limit)
    # expected_curr_size is unchanged as the limit
    # is greater than the current size.
    assert w.storage_usage == expected_curr_size


def test_ensure_dir_on_existing_dir(tmp_path_factory):
    existing = tmp_path_factory.mktemp("exists")
    # This assert checks out if no assertion was raised:
    assert check_and_create_directory(existing) is None

    assert existing.is_dir()


def test_ensure_dir_on_non_existing_dir(tmp_path_factory):
    base = tmp_path_factory.mktemp("base")
    assert base.is_dir()

    non_existing = base / "non_existent"
    assert not non_existing.is_dir()

    # This assert checks out if no assertion was raised:
    assert check_and_create_directory(non_existing) is None

    assert non_existing.is_dir()


def test_ensure_dir_on_file_path(tmp_path):
    a_file = tmp_path.joinpath("a_file")
    a_file.touch()
    with pytest.raises(AssertionError):
        check_and_create_directory(a_file)


@pytest.fixture
def observer() -> Iterator[Observer]:  # type: ignore
    obs = Observer()
    obs.start()
    yield obs
    obs.stop()
    with contextlib.suppress(RuntimeError):
        obs.join()


def test_simple_deletion_watch(observer, tmp_path):
    """
    This tests the simplest behavior emitting filesystem events
    on deletion, regardless whether it is files or directories.
    """

    fs_event = threading.Event()

    class EventHandler(FileSystemEventHandler):
        def on_deleted(self, event: FileSystemEvent) -> None:
            fs_event.set()

    dir_to_watch = tmp_path / "to_delete"
    dir_to_watch.mkdir()

    a_file = dir_to_watch / "a_file"
    a_file.touch()

    observer.schedule(EventHandler(), str(dir_to_watch))

    a_file.unlink()
    assert fs_event.wait()

    fs_event.clear()
    dir_to_watch.rmdir()
    assert fs_event.wait()


def test_directory_deletion_watch(observer, tmp_path):
    """
    This tests the simplest behavior emitting filesystem events
    on deletion, exclusively for directories.
    """

    fs_event = threading.Event()

    class EventHandler(FileSystemEventHandler):
        def on_deleted(self, event: FileSystemEvent) -> None:
            if event.is_directory:
                fs_event.set()

    dir_to_watch = tmp_path / "to_delete"
    dir_to_watch.mkdir()

    a_file = dir_to_watch / "a_file"
    a_file.touch()

    observer.schedule(
        # event_filter not supported on OSX
        EventHandler(),
        str(dir_to_watch),
    )

    a_file.unlink()
    assert not fs_event.wait(0.8)

    dir_to_watch.rmdir()
    assert fs_event.wait()


def test_online_watch_modification(observer, tmp_path):
    """
    This tests whether the observer object can have watches
    dynamically added and removed over its life time.
    """

    fs_event = threading.Event()

    class EventHandler(FileSystemEventHandler):
        def on_deleted(self, event: FileSystemEvent) -> None:
            if event.is_directory:
                fs_event.set()

    dir1_to_watch = tmp_path / "dir1"
    dir1_to_watch.mkdir()
    dir2_to_watch = tmp_path / "dir2"
    dir2_to_watch.mkdir()

    watch1 = observer.schedule(EventHandler(), str(dir1_to_watch))

    dir1_to_watch.rmdir()
    assert fs_event.wait()
    fs_event.clear()

    # Cannot "recycle" a watched location
    dir1_to_watch.mkdir()
    dir1_to_watch.rmdir()
    assert not fs_event.wait(1)
    observer.unschedule(watch1)

    watch2 = observer.schedule(EventHandler(), str(dir2_to_watch))
    dir2_to_watch.rmdir()
    assert fs_event.wait()

    observer.unschedule(watch2)


@pytest.fixture
def directory_monitor() -> Iterator[DirectoryMonitor]:
    obs = DirectoryMonitor()
    obs.start()
    yield obs
    obs.stop()


def test_directory_watcher(directory_monitor, tmp_path):
    """
    This tests the DirectoryMonitor class
    """

    fs_event = threading.Event()

    def on_delete_cb(path: Path) -> None:
        fs_event.set()

    dir1_to_watch = tmp_path / "dir1"
    dir1_to_watch.mkdir()

    directory_monitor.watch(dir1_to_watch, on_delete_cb)
    dir1_to_watch.rmdir()
    assert fs_event.wait()

    with not_raises(KeyError):
        directory_monitor.unwatch(dir1_to_watch)


def test_regular_sequence_update_size(dir_layout, file_creator):
    dir_base, size = dir_layout
    w = StorageSizeWatcher(check_frequency=10)
    w.set_path(dir_base)
    assert w.storage_usage == size

    new_file = create_new(dir_base, file_creator)
    w.incoming(new_file)
    assert w.storage_usage == size + 1

    w.update_file_size(new_file)
    assert w.storage_usage == size + 1

    new_content = b"12345678"
    new_file.write_bytes(new_content)
    w.update_file_size(new_file)
    assert w.storage_usage == size + len(new_content)
