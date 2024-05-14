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
