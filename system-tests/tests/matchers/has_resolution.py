import base64

import cv2
import numpy as np
from hamcrest.core.base_matcher import BaseMatcher
from hamcrest.core.description import Description


class HasResolution(BaseMatcher):
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height

    def _matches(self, item: str) -> bool:
        height, width = self._compute_resolution(item)
        return bool(self.height == height and self.width == width)

    def _compute_resolution(self, b64_image: str) -> tuple[int, int]:
        nparr = np.frombuffer(base64.b64decode(b64_image), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        height, width, _ = img.shape
        return height, width

    def describe_mismatch(self, item: str, mismatch_description: Description) -> None:
        height, width = self._compute_resolution(item)
        mismatch_description.append_text(f"was an {width}x{height} image")

    def describe_to(self, description: Description) -> None:
        description.append_text(f"an {self.width}x{self.height} image")


def has_resolution(width: int, height: int) -> HasResolution:
    return HasResolution(width, height)
