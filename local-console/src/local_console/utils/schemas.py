from typing import Any

from pydantic import RootModel


class ListModel(RootModel):
    def __iter__(self) -> Any:
        return iter(self.root)

    def __getitem__(self, item: int) -> Any:
        return self.root[item]
