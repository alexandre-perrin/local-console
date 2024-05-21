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
from collections.abc import Hashable
from collections.abc import Mapping
from typing import Any
from typing import overload
from typing import TypeVar

from hamcrest.core.description import Description
from hamcrest.core.helpers.wrap_matcher import wrap_matcher
from hamcrest.core.matcher import Matcher
from hamcrest.library.collection.isdict_containingentries import IsDictContainingEntries

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class IsEqual(IsDictContainingEntries):
    # Overwrte IsDictContainingEntries to match equal length Dictionaries

    def matches(
        self, item: Mapping[K, V], mismatch_description: Description | None = None
    ) -> bool:
        if len(item.items()) != len(self.value_matchers):
            if mismatch_description:
                mismatch_description.append_text(f"length is {len(item.items())}")
            return False
        return bool(super().matches(item, mismatch_description))

    def describe_to(self, description: Description) -> None:
        super().describe_to(description)
        description.append_text(f" and length {len(self.value_matchers)}")


# Keyword argument form
@overload
def equal_to(**keys_valuematchers: Matcher[V] | V) -> Matcher[Mapping[str, V]]:
    ...


# Key to matcher dict form
@overload
def equal_to(keys_valuematchers: Mapping[K, Matcher[V] | V]) -> Matcher[Mapping[K, V]]:
    ...


# Alternating key/matcher form
@overload
def equal_to(*keys_valuematchers: Any) -> Matcher[Mapping[Any, Any]]:
    ...


def equal_to(*keys_valuematchers, **kv_args) -> IsEqual:  # type: ignore[no-untyped-def]
    if len(keys_valuematchers) == 1:
        try:
            base_dict = keys_valuematchers[0].copy()
            for key in base_dict:
                base_dict[key] = wrap_matcher(base_dict[key])
        except AttributeError as err:
            raise ValueError(
                "single-argument calls to has_entries must pass a dict as the argument"
            ) from err
    else:
        if len(keys_valuematchers) % 2:
            raise ValueError("has_entries requires key-value pairs")
        base_dict = {}
        for index in range(int(len(keys_valuematchers) / 2)):
            base_dict[keys_valuematchers[2 * index]] = wrap_matcher(
                keys_valuematchers[2 * index + 1]
            )

    for key, value in kv_args.items():
        base_dict[key] = wrap_matcher(value)

    return IsEqual(base_dict)
