from enum import Enum


# NOTE: StrEnum officially added in Python 3.11
class StrEnum(str, Enum):
    def __str__(self) -> str:
        return f"{self.value}"
