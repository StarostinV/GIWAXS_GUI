import logging
import weakref
from copy import deepcopy
from collections import defaultdict, namedtuple
from functools import wraps
from abc import abstractmethod

import numpy as np

from PyQt5.QtCore import QObject, pyqtSignal

from .exceptions.signals import SignalNotFoundError, AppNodeNotProvidedError
from .global_context import Image
from ..utils import RoiParameters

logger = logging.getLogger(__name__)

_SIGNAL_TYPES = ('broadcast', 'onlyForNames', 'exceptForNames')
# TODO change to ENUM

_DEFAULT_SIGNAL_TYPE = 'broadcast'

_GlobalImageObject = Image()
# TODO change to dependency injection


class SignalKeys(object):
    # TODO: change to ENUM
    _image_changed_key = 'image_changed'
    _geometry_changed_key = 'geometry_changed'
    _transformation_key = 'transformation'

    _status_changed_key = 'status_changed'
    _name_changed_key = 'name_changed'
    _scale_changed_key = 'scale_changed'
    _type_changed_key = 'type_changed'

    _segment_created_key = 'segment_created'
    _segment_deleted_key = 'segment_deleted'
    _segment_moved_key = 'segment_moved'

    _segment_fixed_key = 'segment_fixed'
    _segment_unfixed_key = 'segment_unfixed'
    _intensity_limits_changed_key = 'intensity_limits_changed'


_SPECIAL_SIGNAL_TYPES = {
    SignalKeys._name_changed_key: 'exceptForNames',
    SignalKeys._segment_moved_key: 'exceptForNames',
    SignalKeys._geometry_changed_key: 'exceptForNames',
    SignalKeys._type_changed_key: 'exceptForNames'
}


class BasicSignalContainer(object):
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
                self._add_later[signal.name].append(signal)
            else:
                self._signals[signal.name].append(signal)
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

    def remove(self, signal, copy: bool = True) -> 'BasicSignalContainer' or None:
        # TODO: Add option to remove later?
        try:
            self._signals[signal.name].remove(signal)
        except ValueError:
            raise SignalNotFoundError()
        if copy:
            new_container = self.copy()
            self.append(signal)
            return new_container

    def copy(self, copy_add_later: bool = True):
        new_signals_dict = defaultdict(list)
        for signal in self:
            new_signals_dict[signal.name].append(signal.copy())
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


class SignalContainer(BasicSignalContainer, SignalKeys):
    def add_signal(self,
                   signal_name, data, signal_type=None,
                   address_names: list or str = None,
                   add_later: bool = False):
        if not address_names:
            address_names = []
        if isinstance(address_names, str):
            address_names = [address_names]
        if not signal_type:
            signal_type = _SPECIAL_SIGNAL_TYPES.get(
                signal_name, _DEFAULT_SIGNAL_TYPE)
        signal = Signal(data, signal_name, signal_type, address_names)

        if add_later:
            self._add_later[signal.name].append(signal)
        else:
            self.append(signal)
        return self

    # The following functions are shortcuts to simplify syntax.

    @_overload_signal_container_functions
    def image_changed(self, data=None, *args, **kwargs):
        return self._image_changed_key, EmptySignalData

    @_overload_signal_container_functions
    def geometry_changed(self, data=None, *args, **kwargs):
        return self._geometry_changed_key, EmptySignalData

    @_overload_signal_container_functions
    def status_changed(self, data=None, *args, **kwargs):
        return self._status_changed_key, StatusChangedSignal

    @_overload_signal_container_functions
    def segment_created(self, data=None, *args, **kwargs):
        return self._segment_created_key, SegmentSignalData

    @_overload_signal_container_functions
    def segment_moved(self, data=None, *args, **kwargs):
        return self._segment_moved_key, SegmentSignalData

    @_overload_signal_container_functions
    def segment_deleted(self, data=None, *args, **kwargs):
        return self._segment_deleted_key, SegmentSignalData

    @_overload_signal_container_functions
    def segment_fixed(self, data=None, *args, **kwargs):
        return self._segment_fixed_key, SegmentSignalData

    @_overload_signal_container_functions
    def segment_unfixed(self, data=None, *args, **kwargs):
        return self._segment_unfixed_key, SegmentSignalData

    @_overload_signal_container_functions
    def transformation_added(self, data=None, *args, **kwargs):
        return self._transformation_key, EmptySignalData

    @_overload_signal_container_functions
    def intensity_limits_changed(self, data=None, *args, **kwargs):
        return self._intensity_limits_changed_key, EmptySignalData

    @_overload_signal_container_functions
    def name_changed(self, data=None, *args, **kwargs):
        return self._name_changed_key, SegmentSignalData

    @_overload_signal_container_functions
    def scale_changed(self, data=None, *args, **kwargs):
        return self._scale_changed_key, EmptySignalData

    @_overload_signal_container_functions
    def type_changed(self, data=None, *args, **kwargs):
        return self._type_changed_key, SegmentSignalData


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


StatusChangedContainer = namedtuple(
    'StatusChangedSignal', 'keys status change_others')

StatusChangedContainer.__new__.__defaults__ = (True,)


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


class Signal(object):
    __slots__ = ('type', 'name', 'data', 'address_names')

    def __init__(self, data: BasicSignalData,
                 signal_name: str,
                 signal_type: str,
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
        :param signal_name:
        :param address_names:
        """
        if signal_type not in _SIGNAL_TYPES:
            raise ValueError('Unknown signal type.')
        self.type = signal_type
        self.name = signal_name
        self.address_names = address_names
        self.data = data

    def add_name(self, name: str):
        self.address_names.append(name)

    def __call__(self, *args, **kwargs):
        return self.data()

    def __repr__(self):
        return f'Signal {self.name}, type = {self.type}.'

    def copy(self):
        return Signal(self.data, self.name, self.type,
                      deepcopy(self.address_names))

    def __eq__(self, other):
        if (
                self.name == other.name and
                self.address_names == other.address_names and
                self.type == other.type and
                self.data == other.data
        ):
            return True
        return False


class SignalConnector(QObject):
    downwardSignal = pyqtSignal(object)
    upwardSignal = pyqtSignal(object)

    def __init__(self, name: str = None,
                 upper_connector: 'SignalConnector' = None):
        self.NAME = name
        QObject.__init__(self)
        self.image = _GlobalImageObject
        if upper_connector:
            upper_connector.connect_downward(self)

    def get_lower_connector(self, name: str = None) -> 'SignalConnector':
        return SignalConnector(name, self)

    def pass_downward(self, s: SignalContainer) -> SignalContainer or None:
        """Redefine to add additional conditions to pass downward signal
        or to change it."""
        singals_to_remove = list()
        if not s:
            return
        for signal in s:
            if signal.type == 'broadcast':
                continue
            if (self.NAME and signal.type == 'onlyForNames' and
                    self.NAME not in signal.address_names):
                singals_to_remove.append(signal)
            if (self.NAME and signal.type == 'exceptForNames' and
                    self.NAME in signal.address_names):
                singals_to_remove.append(signal)

        for signal in singals_to_remove:
            s = s.remove(signal)
        return s

    def pass_upward(self, s: SignalContainer) -> SignalContainer or None:
        """Redefine to add additional conditions to pass upward signal
        or to change it."""
        if not s:
            return
        for signal in s:
            if self.NAME and signal.type != 'broadcast':
                signal.add_name(self.NAME)
        return s

    def connect_downward(self, lower_connector: 'SignalConnector') -> None:
        self.downwardSignal.connect(lower_connector.emit_downward)
        lower_connector.upwardSignal.connect(self.emit_upward)

    def emit_downward(self, s: SignalContainer):
        s = self.pass_downward(s)
        if s:
            self.downwardSignal.emit(s)

    def emit_upward(self, s: SignalContainer):
        s = self.pass_upward(s)
        if s:
            self.upwardSignal.emit(s)


class AppDataHolder(SignalConnector):

    def __init__(self):
        SignalConnector.__init__(self, 'AppDataHolder')
        self.segments_dict = dict()
        self.selected_keys = list()
        self._status_changed_sent = False
        # only one StatusChangedSignal can be sent in a SignalContainer

    def connect(self, func):
        self.upwardSignal.connect(func)

    def pass_downward(self, s: SignalContainer) -> SignalContainer:

        selected_keys = list()
        # These keys are the keys of created or moved
        # rois. They will form StatusChangedSignal if not empty.
        for _ in s.geometry_changed():
            self.on_geometry_changed(s)

        for _ in s.scale_changed():
            self.on_scale_changed(s)

        for signal in s.segment_deleted():
            key = signal().key
            self.segments_dict.pop(key)
            if key in self.selected_keys:
                self.selected_keys.remove(key)

        for signal in s.segment_created():
            segment = signal()
            signal.data = self.add_segment(segment)
            selected_keys.append(signal().key)
        for signal in s.segment_moved():
            segment = signal()
            self.segments_dict[segment.key] = signal()
            selected_keys.append(signal().key)

        for signal in s.segment_fixed():
            self.segments_dict[signal().key] = signal()

        for signal in s.segment_unfixed():
            self.segments_dict[signal().key] = signal()

        signals_to_remove = list()
        for signal in s.status_changed():
            data_list = self.on_status_changed(signal())
            signals_to_remove.append(signal)
            for data in data_list:
                s.status_changed(data, add_later=True)
        for signal in signals_to_remove:
            s = s.remove(signal)

        for signal in s.name_changed():
            self.segments_dict[signal().key] = signal()
        ##

        if selected_keys and not self._status_changed_sent:
            data = StatusChangedContainer(
                tuple(selected_keys), True, True
            )
            data_list = self.on_status_changed(data)
            for data in data_list:
                s.status_changed(data)

        s.finish_adding_later()
        self._status_changed_sent = False
        return s

    def on_scale_changed(self, s: SignalContainer):
        scale = self.image.scale_change
        for k, v in self.segments_dict.items():
            self.segments_dict[k] = v._replace(radius=v.radius * scale, width=v.width * scale)
            s.segment_moved(self.segments_dict[k], add_later=True)

    def on_geometry_changed(self, s: SignalContainer):
        r_angle, r_angle_std = self.image.ring_angle, self.image.ring_angle_str
        if r_angle is not None and r_angle_std is not None:
            for k, v in self.segments_dict.items():
                if (
                        v.type == RoiParameters.roi_types.ring and
                        (v.angle != r_angle or
                         v.angle_std != r_angle_std)
                ):
                    self.segments_dict[k] = v._replace(
                        angle=r_angle, angle_std=r_angle_std)
                    s.segment_moved(self.segments_dict[k], add_later=True)

    def on_status_changed(self, data: StatusChangedContainer):
        self._status_changed_sent = True
        set_inactive_keys = list()
        set_active_keys = list()
        data_list = list()

        if not data.status:
            for k in data.keys:
                if k in self.selected_keys:
                    set_inactive_keys.append(k)
        else:
            if data.change_others:
                set_inactive_keys = [k for k in self.selected_keys if
                                     k not in data.keys]
            set_active_keys = [k for k in data.keys if
                               k not in self.selected_keys]
            self.selected_keys += set_active_keys
        for k in set_inactive_keys:
            self.selected_keys.remove(k)

        if set_active_keys:
            data_list.append(
                StatusChangedContainer(set_active_keys, True))
        if set_inactive_keys:
            data_list.append(
                StatusChangedContainer(set_inactive_keys, False))
        return data_list

    def emit_upward(self, s: SignalContainer):
        self.emit_downward(s)

    def add_segment(self, segment: RoiParameters) -> SegmentSignalData:
        r_angle, r_angle_std = self.image.ring_angle, self.image.ring_angle_str
        if segment.key is not None:
            new_key = segment.key
            segment = segment._replace(angle=r_angle,
                                       angle_std=r_angle_std)
        else:
            new_key = self._get_new_key()
            segment = segment._replace(key=new_key, angle=r_angle,
                                       angle_std=r_angle_std)
        self.segments_dict[new_key] = segment
        return SegmentSignalData(segment)

    def _get_new_key(self):
        if self.segments_dict:
            return max(self.segments_dict.keys()) + 1
        else:
            return 0


class AppNode(object):
    @property
    def image(self):
        return self.signal_connector.image

    def __init__(self, signal_connector: 'SignalConnector'):
        self.signal_connector = signal_connector

    def get_lower_connector(self, name: str = None):
        return self.signal_connector.get_lower_connector(name)

    def set_beam_center(self, beam_center: tuple):
        self.image.set_beam_center(beam_center)
        self.signal_connector.emit_upward(SignalContainer().geometry_changed(0))

    def set_image(self, image: np.ndarray):
        self.image.set_image(image)
        sc = SignalContainer(app_node=self)
        sc.image_changed(0)
        sc.geometry_changed(0)

    def add_transformation(self, name: str):
        self.image.add_transformation(name)
        sc = SignalContainer()
        sc.transformation_added(0)
        sc.geometry_changed(0)
        self.signal_connector.emit_upward(sc)

    def set_image_limits(self, limits=None):
        if self.image.intensity_limits != limits:
            self.image.set_image_limits(limits)
            SignalContainer().intensity_limits_changed(0).send(self)
