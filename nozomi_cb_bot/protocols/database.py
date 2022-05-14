from typing import Protocol


class CbDatabase(Protocol):
    def update(self):
        ...
