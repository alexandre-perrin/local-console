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
from unittest.mock import AsyncMock
from unittest.mock import Mock

import pytest
from local_console.utils.tracking import TrackingVariable


def test_initialization():
    # Test initialization with no initial value
    var = TrackingVariable()
    assert var.value is None, "Initial value should be None if not provided"
    assert var.previous is None, "Previous value should be None initially"

    # Test initialization with an initial value
    var_with_init = TrackingVariable(10)
    assert var_with_init.value == 10, "Initial value should be as provided"
    assert var_with_init.previous is None, "Previous value should be None initially"


def test_value_update():
    var = TrackingVariable(100)
    assert var.value == 100, "Current value should be set to 100"
    assert (
        var.previous is None
    ), "Previous value should still be None after first update"

    # Update value again to test previous value tracking
    var.value = 200
    assert var.value == 200, "Current value should now be 200"
    assert var.previous == 100, "Previous value should now be 100"


def test_previous_value_tracking():
    var = TrackingVariable()
    values = ["hello", "world", "test"]
    previous_value = None

    for value in values:
        var.value = value
        assert var.value == value, f"Current value should be {value}"
        assert (
            var.previous == previous_value
        ), f"Previous value should be {previous_value}"
        previous_value = value


def test_observers_sync():
    var = TrackingVariable()

    observer = Mock()
    var.subscribe(observer)

    var.value = 42
    observer.assert_called_with(42, None)
    assert observer.call_count == 1

    var.set(11)
    observer.assert_called_with(11, 42)
    assert observer.call_count == 2

    var.unsubscribe(observer)

    var.value = 0
    assert observer.call_count == 2


@pytest.mark.trio
async def test_observers_async():
    var = TrackingVariable()

    observer = AsyncMock()
    var.subscribe_async(observer)

    await var.aset(42)
    observer.assert_awaited_with(42, None)
    assert observer.call_count == 1

    await var.aset(11)
    observer.assert_awaited_with(11, 42)
    assert observer.await_count == 2

    var.unsubscribe_async(observer)

    await var.aset(0)
    assert observer.await_count == 2
