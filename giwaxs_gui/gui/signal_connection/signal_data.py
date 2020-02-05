import logging
from copy import deepcopy
from typing import NamedTuple
from abc import abstractmethod

import numpy as np

from ...utils import RoiParameters

logger = logging.getLogger(__name__)

__all__ = ['BasicSignalData', 'SegmentSignalData',
           'StatusChangedSignal', 'NumpySignalData', 'StatusChangedContainer',
           'EmptySignalData']


class BasicSignalData(object):
    def __init__(self, data):
        self._data = data

    def __call__(self):
        return self._data

    @abstractmethod
    def __eq__(self, other):
        pass

    def copy(self):
        return self.__class__(deepcopy(self()))

    def __repr__(self):
        return f'Signal data {self.__class__}: {str(self._data)}'


class EmptySignalData(BasicSignalData):
    def __init__(self, *args):
        super().__init__(None)

    def __eq__(self, other):
        return True


class ImmutableSignalData(BasicSignalData):
    def __eq__(self, other):
        return self() == other()

    def copy(self):
        return self.__class__(self())

    def __repr__(self):
        return self._data


class StatusChangedContainer(NamedTuple):
    keys: list
    status: bool
    change_others: bool = True


class StatusChangedSignal(ImmutableSignalData):
    """
    This signal should not appear more than once in
    a SignalContainer.
    """

    def __init__(self, data: StatusChangedContainer):
        ImmutableSignalData.__init__(self, data)


class SegmentSignalData(ImmutableSignalData):
    def __call__(self) -> RoiParameters:
        return self._data


class NumpySignalData(BasicSignalData):
    def __eq__(self, other):
        return np.all(self() == other())
