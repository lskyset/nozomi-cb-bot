from typing import Protocol


class Ui(Protocol):
    def update(self) -> None:
        ...
