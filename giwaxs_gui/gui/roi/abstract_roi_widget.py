# -*- coding: utf-8 -*-
from abc import abstractmethod

from PyQt5.QtCore import pyqtSignal

from .colors import COLOR_DICT
from ..signal_connection import StatusChangedContainer, SignalContainer
from ...utils import RoiParameters


class AbstractROI(object):
    value_changed = pyqtSignal(RoiParameters)
    status_changed = pyqtSignal(StatusChangedContainer)
    arbitrary_signal = pyqtSignal(SignalContainer)
    signal_by_key = pyqtSignal(tuple)

    _USE_BRIGHT_COLOR = False

    @property
    def color(self):
        # TODO: set colors independently for better customization?
        value = self.parameters
        if value.movable and self._active:
            return COLOR_DICT['active_bright'] if self._USE_BRIGHT_COLOR else COLOR_DICT['active']
        if value.movable and not self._active:
            return COLOR_DICT['inactive_bright'] if self._USE_BRIGHT_COLOR else COLOR_DICT['inactive']
        if not value.movable and self._active:
            return COLOR_DICT['fixed_active_bright'] if self._USE_BRIGHT_COLOR else COLOR_DICT['fixed_active']
        if not value.movable and not self._active:
            return COLOR_DICT['fixed_bright'] if self._USE_BRIGHT_COLOR else COLOR_DICT['fixed']

    def __init__(self, value: RoiParameters):
        self.parameters = value
        self.key = value.key
        self._active = False

    def init_roi(self):
        self.set_inactive()
        self.set_value(self.parameters)
        if not self.parameters.movable:
            self.set_fixed()

    @property
    def active(self):
        return self._active

    @property
    @abstractmethod
    def value(self):
        """
        Value is an instance of RoiParameters class.
        :return:
        """
        pass

    @value.setter
    @abstractmethod
    def value(self, value: RoiParameters):
        """
        Value is an instance of RoiParameters class.
        :param value: RoiParameters
        :return:
        """
        pass

    def set_value(self, value):
        if self.value != value:
            self.value = value

    @abstractmethod
    def set_active(self):
        pass

    @abstractmethod
    def set_inactive(self):
        pass

    def change_active(self, change_others: bool = True):
        if self._active:
            self.send_inactive()
        else:
            self.send_active(change_others)
# TODO: replace by abstractmethod s: set_color(), set_movable(bool)
    @abstractmethod
    def set_fixed(self):
        pass

    @abstractmethod
    def set_unfixed(self):
        pass

    def send_value(self):
        self.value_changed.emit(self.value)

    def send_active(self, change_others: bool = True):
        self.status_changed.emit(StatusChangedContainer(
            [self.key], True, change_others))

    def send_name(self, name: str, **kwargs):
        self.set_name(name)
        self.arbitrary_signal.emit(SignalContainer().name_changed(self.value, **kwargs))

    def set_name(self, name: str):
        self.parameters = self.parameters._replace(name=name)
        # logger.debug(self.value)

    def send_inactive(self):
        self.status_changed.emit(StatusChangedContainer(
            [self.key], False))

    def send_signal(self, signal_container: SignalContainer):
        self.arbitrary_signal.emit(signal_container)

    def __repr__(self):
        return str(self.parameters)