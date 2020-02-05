import logging

from PyQt5.QtCore import QObject, pyqtSignal

from .signal_types import SignalTypes
from .signal_data import (SegmentSignalData, StatusChangedContainer)
from .signal_container import SignalContainer

from ..global_context import Image
from ...utils import RoiParameters

logger = logging.getLogger(__name__)

__all__ = ['SignalConnector', 'AppDataHolder']

_GlobalImageObject = Image()


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
            if signal.type == SignalTypes.broadcast:
                continue
            if (self.NAME and signal.type == SignalTypes.only_for_names and
                    self.NAME not in signal.address_names):
                singals_to_remove.append(signal)
            if (self.NAME and signal.type == SignalTypes.except_for_names and
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
            if self.NAME and signal.type != SignalTypes.broadcast:
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
                selected_keys, True, True
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
