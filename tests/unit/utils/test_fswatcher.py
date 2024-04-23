import random
from collections import OrderedDict
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from wedge_cli.utils.fswatch import StorageSizeWatcher


@pytest.fixture
def dir_layout(tmpdir):
    entries = [
        tmpdir.join("fileA"),
        tmpdir.join("fileB"),
        tmpdir.mkdir("sub").join("file0"),
        tmpdir.join("sub").mkdir("subsub").join("file0"),
    ]
    # Make all entries, files of size 1
    for e in entries:
        e.write_binary(b"0")

    return [Path(tmpdir), len(entries)]


class walk_entry_mock:
    def __init__(self) -> None:
        self.age = 0

    def __call__(self, path: Path) -> tuple[tuple[int, Path], int]:
        size = 1
        age = self.age
        self.age += 1
        return (age, path), size


def create_new(root: Path) -> Path:
    new_file = root / f"{random.randint(1, 1e6)}"
    new_file.write_bytes(b"0")
    return new_file


def test_regular_sequence(dir_layout):
    dir_base, size = dir_layout
    with patch("wedge_cli.utils.fswatch.walk_entry", walk_entry_mock()):
        w = StorageSizeWatcher(check_frequency=10)
        assert w.state == StorageSizeWatcher.State.Start

        w.set_path(dir_base)
        assert w.state == StorageSizeWatcher.State.Accumulating
        assert w.storage_usage == size

        w.incoming(create_new(dir_base))
        assert w.state == StorageSizeWatcher.State.Accumulating
        assert w.storage_usage == size + 1
        size += 1

        oldest_age, _ = w.get_oldest()
        assert oldest_age == 0

        st_limit = 4
        w.set_storage_limit(st_limit)
        oldest_age, _ = w.get_oldest()
        assert oldest_age == 1
        assert w.storage_usage == st_limit
        assert w._consistency_check()

        # Test creating and registering new files
        # in lockstep
        num_new_files = random.randint(5, 20)
        for _ in range(num_new_files):
            w.incoming(create_new(dir_base))
        assert w._consistency_check()
        assert w.storage_usage == st_limit
        expected_oldest_age = oldest_age + num_new_files
        oldest_age, _ = w.get_oldest()
        # This is due to the timestamp mocking, as each new file
        # is timestamped one time unit later than the previous.
        assert oldest_age == expected_oldest_age

        # Test creating and registering new files
        # not in lockstep
        num_new_files = random.randint(5, 20)
        for _ in range(num_new_files):
            create_new(dir_base)
        # although consistency_check restores consistency,
        # it returns whether state was consistent before
        assert not w._consistency_check()
        # hence, a further call should indicate consistency.
        assert w._consistency_check()
        expected_oldest_age = oldest_age + num_new_files

        # However, pruning is still necessary:
        oldest_age, _ = w.get_oldest()
        assert oldest_age != expected_oldest_age
        assert w.storage_usage != st_limit
        w._prune()
        oldest_age, _ = w.get_oldest()
        assert oldest_age == expected_oldest_age
        assert w.storage_usage == st_limit


def test_incoming_always_prunes(dir_layout):
    dir_base, size = dir_layout
    mock_prune = Mock()
    with patch("wedge_cli.utils.fswatch.walk_entry", walk_entry_mock()), patch.object(
        StorageSizeWatcher, "_prune", mock_prune
    ):
        w = StorageSizeWatcher(check_frequency=10)
        w.set_path(dir_base)
        st_limit = 4
        assert mock_prune.call_count == 0
        w.set_storage_limit(st_limit)
        assert mock_prune.call_count == 1

        num_new_files = random.randint(5, 20)
        for _ in range(num_new_files):
            w.incoming(create_new(dir_base))
        assert mock_prune.call_count == num_new_files + 1


def test_remaining_before_consistency_check(dir_layout):
    check_frequency = 10
    storage_limit = 4

    dir_base, size = dir_layout
    mock_prune = Mock()
    with patch("wedge_cli.utils.fswatch.walk_entry", walk_entry_mock()), patch.object(
        StorageSizeWatcher, "_prune", mock_prune
    ):
        w = StorageSizeWatcher(check_frequency=check_frequency)
        w.set_path(dir_base)
        w.set_storage_limit(storage_limit)
        assert w._remaining_before_check == check_frequency

        for i in range(check_frequency):
            assert w._remaining_before_check == check_frequency - i
            w.incoming(create_new(dir_base))
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
