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
from typing import Callable
from typing import Generic
from typing import Optional
from typing import TypeVar

T = TypeVar("T")
OptT = Optional[T]
Obs = Callable[[OptT, OptT], None]
ObsAsync = Callable[[OptT, OptT], Awaitable[None]]


class TrackingVariable(Generic[T]):
    """
    This class implements a variable that exposes .previous
    property for getting the previous value assigned to it.
    For the current value, read and assignment works as usual
    """

    def __init__(self, initial_value: OptT = None) -> None:
        self._current_value: OptT = initial_value
        self._previous_value: OptT = None
        self._observers: list[Obs] = []
        self._observers_async: list[ObsAsync] = []

    @property
    def value(self) -> OptT:
        """Get the current value of the variable."""
        return self._current_value

    @value.setter
    def value(self, new_value: OptT) -> None:
        """Set a new value for the variable, updating the previous value."""
        self._previous_value = self._current_value
        self._current_value = new_value

        # Invoke synchronous observers
        for obs in self._observers:
            obs(self.value, self.previous)

    def set(self, new_value: OptT) -> None:
        """
        Method for setting the value.
        Useful to avoid using lambdas
        """
        self.value = new_value

    async def aset(self, new_value: OptT) -> None:
        """Value setter for using in an async context"""
        self.value = new_value

        # Invoke asynchronous observers
        for obs in self._observers_async:
            await obs(self.value, self.previous)

    @property
    def previous(self) -> OptT:
        """Get the previous value of the variable."""
        return self._previous_value

    def __repr__(self) -> str:
        return f"Current Value: {self.value}, Previous Value: {self.previous}"

    def subscribe(self, observer: Obs) -> None:
        self._observers.append(observer)

    def unsubscribe(self, observer: Obs) -> None:
        self._observers.remove(observer)

    def subscribe_async(self, observer: ObsAsync) -> None:
        self._observers_async.append(observer)

    def unsubscribe_async(self, observer: ObsAsync) -> None:
        self._observers_async.remove(observer)
