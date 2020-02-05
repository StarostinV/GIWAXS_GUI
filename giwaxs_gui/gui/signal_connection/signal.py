import logging

from copy import deepcopy
from .signal_keys import SignalKeys
from .signal_types import SignalTypes
from .signal_data import BasicSignalData

logger = logging.getLogger(__name__)

__all__ = ['Signal']


class Signal(object):
    __slots__ = ('type', 'key', 'data', 'address_names')

    def __init__(self, data: 'BasicSignalData',
                 signal_key: SignalKeys,
                 signal_type: SignalTypes,
                 address_names: list = None):
        """
        Signal is emitted in SignalContainer through the SignalConnector.
        It contains the data needed to be sent and additional attributes.

        'signal_type' can be one of 'broadcast', 'exceptForNames', 'onlyForNames'.
        'broadcast' is translated to all the signal connectors;
        'exceptForNames' is ignored by SignalConnector with NAME in 'address_names';
        'onlyForNames' is accepted by SignalConnector with NAME in 'address_names'.

        'signal_name' is a name representing specific functionality
        of the application.

        :param data:
        :param signal_type:
        :param signal_key:
        :param address_names:
        """
        if signal_type not in SignalTypes.__members__.values():
            raise ValueError('Unknown signal type.')
        self.type = signal_type
        self.key = signal_key
        self.address_names = address_names
        self.data = data

    def add_name(self, name: str):
        self.address_names.append(name)

    def __call__(self, *args, **kwargs):
        return self.data()

    def __repr__(self):
        return f'Signal {self.key}, type = {self.type}.'

    def copy(self):
        return Signal(self.data, self.key, self.type,
                      deepcopy(self.address_names))

    def __eq__(self, other):
        if (
                self.key == other.key and
                self.address_names == other.address_names and
                self.type == other.type and
                self.data == other.data
        ):
            return True
        return False
