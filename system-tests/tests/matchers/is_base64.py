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
import base64
from typing import Union

from hamcrest.core.base_matcher import BaseMatcher
from hamcrest.core.description import Description


class IsBase64(BaseMatcher):
    # Match String is Base64

    def _matches(self, item: Union[str, bytes]) -> bool:
        matches = False
        try:
            base64.b64decode(item)
            matches = True
        except base64.binascii.Error:
            pass

        return matches

    def describe_to(self, description: Description) -> None:
        description.append_text("a base64 string")


def is_base64() -> IsBase64:
    return IsBase64()
