from typing import Callable

import trio


class TimeoutBehavior:
    def __init__(self, timeout: float, callback: Callable):
        self.timeout_secs = timeout
        self.callback = callback

        self._event_flag = trio.Event()

    def tap(self) -> None:
        """
        Avoid timer expiration
        """
        self._event_flag.set()

    def spawn_in(self, nursery: trio.Nursery) -> None:
        nursery.start_soon(self.timeout_behavior_task)

    async def timeout_behavior_task(self) -> None:
        """
        This task will call the given callable if the
        event flag has not been refreshed within the timeout period,
        specified in seconds as per trio.move_on_after().
        """
        while True:
            with trio.move_on_after(self.timeout_secs) as time_cs:
                await self._event_flag.wait()
                time_cs.deadline += self.timeout_secs
                self._event_flag = trio.Event()

            if time_cs.cancelled_caught:
                await self.callback()
