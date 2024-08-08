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
from collections.abc import Awaitable
from collections.abc import Iterable
from queue import Queue
from typing import Any
from typing import Callable
from typing import Optional

import trio
from kivy.clock import Clock

AsyncFunc = Callable[..., Awaitable[Any]]
WorkItem = tuple[AsyncFunc, tuple[Any]]


class SyncAsyncBridge:
    """
    This class enables calling async functions from synchronous places
    such as Kivy's events, which are not async despite the Kivy event
    loop being provided by Trio.
    """

    def __init__(self) -> None:
        self.tasks_queue: Queue[Optional[WorkItem]] = Queue()

    # Function to post tasks to the Trio thread from Kivy
    def enqueue_task(self, func: AsyncFunc, *args: Any) -> None:
        self.tasks_queue.put((func, args))

    def has_pending(self) -> bool:
        return not self.tasks_queue.empty()

    def close_task_queue(self) -> None:
        self.tasks_queue.put(None)

    # Async task listener
    async def bridge_listener(self) -> None:
        async with trio.open_nursery() as nursery:
            while True:
                # Wait for tasks from the queue
                assert self.tasks_queue
                items: Optional[WorkItem] = await trio.to_thread.run_sync(
                    self.tasks_queue.get
                )
                if items is None:
                    break
                else:
                    func: AsyncFunc = items[0]
                    args: Iterable[Any] = items[1]
                    nursery.start_soon(func, *args)


def run_on_ui_thread(func: Callable) -> Callable:
    def wrapper(*args: Any, **kwargs: Any) -> None:
        def callback(dt: float) -> None:
            func(*args, **kwargs)

        Clock.schedule_once(callback)

    return wrapper
