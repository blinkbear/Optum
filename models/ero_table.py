from typing import Iterable


class EROTable(dict):
    def __setitem__(self, key: Iterable, value: float) -> None:
        return super().__setitem__(tuple(sorted(key)), value)

    def __getitem__(self, key: Iterable) -> float:
        return super().__getitem__(tuple(sorted(key)))

    def get(self, key: Iterable, default) -> float:
        return super().get(tuple(sorted(key)), default)
