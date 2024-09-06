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
import enum
import logging
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from typing import Optional

from watchdog.events import DirDeletedEvent
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import ObservedWatch


logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    age: int
    path: Path
    size: int


class WatchException(Exception):
    pass


class StorageSizeWatcher:
    class State(enum.Enum):
        Start = enum.auto()
        Accumulating = enum.auto()
        Checking = enum.auto()

    def __init__(self, check_frequency: int = 50) -> None:
        """
        Class for watching a directory for incoming files while maintaining
        the total storage usage within the directory under a given limit size,
        pruning the oldest files when necessary.

        Bookkeeping is made in-memory for it to remain fast, however consistency
        is checked against the filesystem once every given number of incoming
        files.

        Args:
                check_frequency (int, optional): check consistency after this many new files. Defaults to 50.
        """
        self.check_frequency = check_frequency
        self._paths: set[Path] = set()
        self.state = self.State.Start
        self._size_limit: Optional[int] = None
        self.content: list[FileInfo] = []
        self.storage_usage = 0
        self._remaining_before_check = self.check_frequency

    def set_path(self, path: Path) -> None:
        assert path.is_dir()

        p = path.resolve()
        if p in self._paths:
            return
        self._paths.add(p)

        # Execute regardless of current state
        self._build_content_list(path)

    def unwatch_path(self, path: Path) -> None:
        assert path.is_dir()
        self._paths.discard(path.resolve())

    def set_storage_limit(self, limit: int) -> None:
        logger.debug(f"Setting storage limit to {limit} bytes")
        assert limit >= 0

        self._size_limit = limit
        if self.state == self.State.Accumulating:
            self._prune()

    def incoming(self, path: Path) -> None:
        assert path.is_file()

        if not self._paths:
            return

        if not any(path.resolve().is_relative_to(root) for root in self._paths):
            raise WatchException(
                f"Incoming file {path} does not belong to either of {self._paths}"
            )

        if self.state == self.State.Accumulating:
            self._register_file(path)

            self._remaining_before_check -= 1
            if self._remaining_before_check == 0:
                self._consistency_check()
                self._remaining_before_check = self.check_frequency

            self._prune()
        else:
            logger.warning(
                f"Deferring update of size statistic for incoming file {path} during state {self.state}"
            )

    def update_file_size(self, path: Path) -> None:
        # TODO: Optimize. Assumption: updates on files are for the newest ones.
        curr = len(self.content)
        while curr > 0:
            if self.content[curr - 1].path == path:
                entry = walk_entry(path)
                self.storage_usage -= self.content[curr - 1].size
                self.storage_usage += entry.size
                self.content[curr - 1].size = entry.size
                return
            curr -= 1
        logger.warning(f"Requested update of the size of {path} but does not exist")

    def get_oldest(self) -> Optional[FileInfo]:
        if self.content:
            return self.content[0]
        else:
            return None

    def _register_file(self, path: Path) -> None:
        entry = walk_entry(path)
        self.storage_usage += entry.size
        curr = len(self.content)
        while curr > 0:
            if self.content[curr - 1].age < entry.age:
                self.content.insert(curr, entry)
                return
            curr -= 1

        # if older than all elements
        self.content.insert(0, entry)

    def _unregister_file(self, path: Path) -> None:
        new_content = []
        for entry in self.content:
            if entry.path == path:
                self.storage_usage -= entry.size
            else:
                new_content.append(entry)
        self.content = new_content

    def _build_content_list(self, root: Path) -> None:
        """
        Adds to `self.content` the FileInfo of files under `root` directory.
        """
        assert self._paths
        self.state = self.State.Accumulating

        new_files = list(walk_files(root))

        self.content = sorted(
            new_files + self.content,
            key=lambda e: e.age,
        )
        self.storage_usage += sum(e.size for e in new_files)

    def _prune(self) -> None:
        if self._size_limit is None:
            return

        # In order to make this class thread-safe,
        # the following would be required:
        # self.state == self.State.Checking
        while self.storage_usage > self._size_limit:
            try:
                entry = self.content.pop(0)
                entry.path.unlink()
                self.storage_usage -= entry.size
            except FileNotFoundError:
                logger.warning(f"File {entry.path} was already removed")
            except KeyError:
                break

        # In order to make this class thread-safe,
        # the following would be required:
        # self.state == self.State.Accumulating

    def _consistency_check(self) -> bool:
        assert self._paths
        in_memory = {k.path for k in self.content}
        in_storage = {p.path for root in self._paths for p in walk_files(root)}

        difference = in_storage - in_memory
        if difference:
            logger.warning(
                f"File bookkeeping inconsistency: new files on disk are: {difference}"
            )
            for path in difference:
                self._register_file(path)
            return False

        difference = in_memory - in_storage
        if difference:
            logger.warning(
                f"File bookkeeping inconsistency: files unexpectedly removed: {difference}"
            )
            for path in difference:
                self._unregister_file(path)
            return False

        return True


def walk_entry(path: Path) -> FileInfo:
    st = os.stat(path)
    file_age = st.st_mtime_ns
    file_size = st.st_size
    return FileInfo(file_age, path, file_size)


def walk_files(root: Path) -> Iterator[FileInfo]:
    # Use os.scandir, https://peps.python.org/pep-0471/, to improve performance by getting stats
    # without additional system calls in most of the cases
    for entry in os.scandir(root):
        if entry.is_file():
            stat = entry.stat()
            yield FileInfo(stat.st_mtime_ns, Path(entry.path), stat.st_size)
        elif entry.is_dir():
            yield from walk_files(Path(entry.path))


def check_and_create_directory(directory: Path) -> None:
    if not directory.exists():
        logger.warning(f"{directory} does not exist. Creating directory...")
        directory.mkdir(exist_ok=True, parents=True)
    else:
        assert directory.is_dir()


OnDeleteCallable = Callable[[Path], None]


class DirectoryMonitor:

    class EventHandler(FileSystemEventHandler):
        def __init__(self, on_delete_cb: OnDeleteCallable) -> None:
            self._on_delete_cb = on_delete_cb

        def on_deleted(self, event: DirDeletedEvent) -> None:
            if event.is_directory:
                self._on_delete_cb(event)

    def __init__(self) -> None:
        self._obs = Observer()
        self._watches: dict[Path, ObservedWatch] = dict()

    def start(self) -> None:
        self._obs.start()

    def watch(self, directory: Path, on_delete_cb: OnDeleteCallable) -> None:
        assert directory.is_dir()
        resolved = directory.resolve()
        handler = self.EventHandler(self._watch_decorator(on_delete_cb))
        watch = self._obs.schedule(
            handler,
            str(resolved),
        )
        self._watches[resolved] = watch

    def _on_delete_action(self, path: Path) -> None:
        resolved = path.resolve()
        watch = self._watches.pop(resolved)
        self._obs.unschedule(watch)

    def _watch_decorator(self, on_delete_cb: OnDeleteCallable) -> Callable:

        def complete_callback(event: DirDeletedEvent) -> None:
            path = Path(event.src_path)
            self._on_delete_action(path)
            on_delete_cb(path)

        return complete_callback

    def unwatch(self, directory: Path) -> None:
        try:
            self._on_delete_action(directory)
        except KeyError:
            pass

    def stop(self) -> None:
        self._obs.stop()
        with contextlib.suppress(RuntimeError):
            self._obs.join()
