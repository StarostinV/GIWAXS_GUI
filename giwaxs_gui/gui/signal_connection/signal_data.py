from typing import NamedTuple

__all__ = ['StatusChangedContainer']


class StatusChangedContainer(NamedTuple):
    keys: list
    status: bool
    change_others: bool = True
