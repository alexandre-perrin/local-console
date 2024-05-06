import re

from hamcrest.core.base_matcher import BaseMatcher
from hamcrest.core.description import Description


class IsBase64(BaseMatcher):
    # Match String is Base64

    def _matches(self, item: str) -> bool:
        return (
            re.match(
                r"^([A-Za-z0-9+/]{4})*([A-Za-z0-9+/]{3}=|[A-Za-z0-9+/]{2}==)?$", item
            )
            is not None
        )

    def describe_to(self, description: Description) -> None:
        description.append_text("a base64 string")


def is_base64() -> IsBase64:
    return IsBase64()
