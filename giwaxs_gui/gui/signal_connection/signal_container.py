import logging
import weakref

from collections import defaultdict

from functools import wraps

from .signal_keys import SignalKeys
from .signal_types import SignalTypes, _get_type_by_key
from .signal_data import (SegmentSignalData,
                          EmptySignalData, StatusChangedSignal)
from .signal import Signal
from ..exceptions import SignalNotFoundError, AppNodeNotProvidedError

logger = logging.getLogger(__name__)

__all__ = ['SignalContainer']


class BasicSignalContainer(object):
    SignalKeys = SignalKeys
    SignalTypes = SignalTypes

    @property
    def adding_finished(self):
        return bool(self._add_later)

    @property
    def app_node(self):
        return self._app_node() if self._app_node else None

    def __init__(self, signals: defaultdict = None, app_node: 'AppNode' = None):
        self._signals = signals or defaultdict(list)
        self._add_later = defaultdict(list)
        self._app_node = weakref.ref(app_node) if app_node else None

    def send(self, app_node=None):
        app_node = app_node or self.app_node
        if not app_node:
            raise AppNodeNotProvidedError()
        app_node.signal_connector.emit_upward(self)

    def append(self, signal: 'Signal', copy: bool = False,
               add_later: bool = False):
        if not copy:
            if add_later:
                self._add_later[signal.key].append(signal)
            else:
                self._signals[signal.key].append(signal)
        else:
            new_container = self.copy()
            new_container.append(signal, add_later=add_later)
            return new_container

    def append_later(self, signal: 'Signal'):
        self.append(signal, add_later=True)

    def finish_adding_later(self):
        for k, v in self._add_later.items():
            self._signals[k] += v
        self._add_later = defaultdict(list)

    def remove(self, signal: 'Signal', copy: bool = True) -> 'BasicSignalContainer' or None:
        # TODO: Add option to remove later?
        try:
            self._signals[signal.key].remove(signal)
        except ValueError:
            raise SignalNotFoundError()
        if copy:
            new_container = self.copy()
            self.append(signal)
            return new_container

    def copy(self, copy_add_later: bool = True):
        new_signals_dict = defaultdict(list)
        for signal in self:
            new_signals_dict[signal.key].append(signal.copy())
        new_container = self.__class__(new_signals_dict)
        if copy_add_later:
            for k, v in self._add_later.items():
                new_container._add_later[k] += [signal.copy() for signal in v]
        return new_container

    def __iter__(self):
        for key in self._signals.keys():
            for signal in self._signals[key]:
                yield signal

    def __getitem__(self, item):
        return self._signals[item]

    def __repr__(self):
        return '\n'.join([str(signal) for signal in self])


def _overload_signal_container_functions(func):
    @wraps(func)
    def wrapper(self, data=None, *args, **kwargs):
        key, data_class = func(self)
        if data is None:
            return self[key]
        else:
            self.add_signal(key, data_class(data),
                            *args, **kwargs)
            return self

    return wrapper


class SignalContainer(BasicSignalContainer):
    def add_signal(self,
                   signal_name: SignalKeys, data, signal_type: SignalTypes = None,
                   address_names: list or str = None,
                   add_later: bool = False):
        if not address_names:
            address_names = []
        if isinstance(address_names, str):
            address_names = [address_names]
        if not signal_type:
            signal_type = _get_type_by_key(signal_name)
        signal = Signal(data, signal_name, signal_type, address_names)

        if add_later:
            self._add_later[signal.key].append(signal)
        else:
            self.append(signal)
        return self

    # The following functions are shortcuts to simplify syntax.

    @_overload_signal_container_functions
    def image_changed(self, data=None, *args, **kwargs):
        return SignalKeys.image_changed, EmptySignalData

    @_overload_signal_container_functions
    def geometry_changed(self, data=None, *args, **kwargs):
        return SignalKeys.geometry_changed, EmptySignalData

    @_overload_signal_container_functions
    def geometry_changed_finish(self, data=None, *args, **kwargs):
        return SignalKeys.geometry_changed_finish, EmptySignalData

    @_overload_signal_container_functions
    def status_changed(self, data=None, *args, **kwargs):
        return SignalKeys.status_changed, StatusChangedSignal

    @_overload_signal_container_functions
    def segment_created(self, data=None, *args, **kwargs):
        return SignalKeys.segment_created, SegmentSignalData

    @_overload_signal_container_functions
    def segment_moved(self, data=None, *args, **kwargs):
        return SignalKeys.segment_moved, SegmentSignalData

    @_overload_signal_container_functions
    def segment_deleted(self, data=None, *args, **kwargs):
        return SignalKeys.segment_deleted, SegmentSignalData

    @_overload_signal_container_functions
    def segment_fixed(self, data=None, *args, **kwargs):
        return SignalKeys.segment_fixed, SegmentSignalData

    @_overload_signal_container_functions
    def segment_unfixed(self, data=None, *args, **kwargs):
        return SignalKeys.segment_unfixed, SegmentSignalData

    @_overload_signal_container_functions
    def transformation_added(self, data=None, *args, **kwargs):
        return SignalKeys.transformation_added, EmptySignalData

    @_overload_signal_container_functions
    def intensity_limits_changed(self, data=None, *args, **kwargs):
        return SignalKeys.intensity_limits_changed, EmptySignalData

    @_overload_signal_container_functions
    def name_changed(self, data=None, *args, **kwargs):
        return SignalKeys.name_changed, SegmentSignalData

    @_overload_signal_container_functions
    def scale_changed(self, data=None, *args, **kwargs):
        return SignalKeys.scale_changed, EmptySignalData

    @_overload_signal_container_functions
    def type_changed(self, data=None, *args, **kwargs):
        return SignalKeys.type_changed, SegmentSignalData
