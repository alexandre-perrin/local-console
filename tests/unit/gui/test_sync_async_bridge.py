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
import pytest
import trio
from local_console.gui.utils.sync_async import SyncAsyncBridge


@pytest.mark.trio
async def test_submit_item(nursery):
    bridge = SyncAsyncBridge()

    flag = trio.Event()

    async def work_func(flag: trio.Event) -> None:
        flag.set()

    # Submit the work item...
    bridge.enqueue_task(work_func, flag)
    # ... but it doesn't run since the listener has not started
    assert not flag.is_set()
    assert bridge.has_pending()

    # Start the listener
    nursery.start_soon(bridge.bridge_listener)

    # now the item should be picked up
    await flag.wait()
    assert not bridge.has_pending()

    # make the listener stop
    bridge.close_task_queue()

    # Submit another work item...
    bridge.enqueue_task(work_func, flag)

    # See that it doesn't run after the queue has been closed
    assert bridge.has_pending()
