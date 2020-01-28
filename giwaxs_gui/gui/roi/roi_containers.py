# -*- coding: utf-8 -*-
from abc import abstractmethod

from ..exceptions.roi import KeySignalNameError
from ..signal_connection import (AppNode, SignalConnector, SignalContainer,
                                 StatusChangedContainer)
from ...utils import RoiParameters


class AbstractROIContainer(AppNode):
    def __init__(self, signal_connector: SignalConnector):
        AppNode.__init__(self, signal_connector)
        self.signal_connector.downwardSignal.connect(self.process_signal)
        self.roi_dict = dict()

    def process_signal(self, s: SignalContainer):
        for signal in s.segment_created():
            self.add_roi(signal())
        for signal in s.segment_moved():
            self.roi_dict[signal().key].value = signal()
        for signal in s.segment_deleted():
            self.delete_roi(signal())
        for signal in s.segment_fixed():
            self.roi_dict[signal().key].set_fixed()
        for signal in s.segment_unfixed():
            self.roi_dict[signal().key].set_unfixed()
        for signal in s.status_changed():
            self._on_status_changed(signal())
        for signal in s.name_changed():
            self.roi_dict[signal().key].set_name(signal().name)
        for signal in s.type_changed():
            self.on_type_changed(signal())

    @abstractmethod
    def _get_roi(self, params: RoiParameters) -> 'AbstractROI':
        pass

    @abstractmethod
    def _add_item(self, roi: 'AbstractROI'):
        pass

    @abstractmethod
    def _remove_item(self, roi: 'AbstractROI'):
        pass

    def _on_status_changed(self, sig: StatusChangedContainer):
        if not sig.status:
            for k in sig.keys:
                self.roi_dict[k].set_inactive()
        else:
            for k in sig.keys:
                self.roi_dict[k].set_active()

    def emit_create_segment(self, params: RoiParameters):
        self.signal_connector.emit_upward(
            SignalContainer().segment_created(params))

    def emit_delete_segment(self, params: RoiParameters):
        self.signal_connector.emit_upward(
            SignalContainer().segment_deleted(params))

    def emit_status_changed(self, sig: StatusChangedContainer):
        if (not sig.status and
                len(sig.keys) == 1 and
                set([roi.key for roi in self.get_selected()]).difference(sig.keys)):
            sig = sig._replace(status=True, change_others=True)
        SignalContainer(app_node=self).status_changed(sig).send()

    def add_roi(self, params: RoiParameters):
        roi = self._get_roi(params)
        if roi:
            roi.value_changed.connect(self.send_value_changed)
            roi.status_changed.connect(self.emit_status_changed)
            roi.arbitrary_signal.connect(self.signal_connector.emit_upward)
            self.roi_dict[params.key] = roi
            self._add_item(roi)
            return roi

    def delete_roi(self, params: RoiParameters):
        roi = self.roi_dict.pop(params.key)
        self._remove_item(roi)
        roi.deleteLater()

    def get_selected(self):
        return [roi.parameters for roi in self.roi_dict.values() if roi.active]

    def send_value_changed(self, value: RoiParameters):
        SignalContainer(app_node=self).segment_moved(value).send()

    def on_type_changed(self, value: RoiParameters):
        self.roi_dict[value.key].value = value


class BasicROIContainer(AbstractROIContainer):
    def add_roi(self, params: RoiParameters):
        roi = AbstractROIContainer.add_roi(self, params)
        if roi:
            roi.signal_by_key.connect(self.resend_key_signal)
        return roi

    def resend_key_signal(self, key: tuple):
        key, args = key[0], key[1:]
        method = getattr(self, key, None)
        if not method:
            raise KeySignalNameError()
        method(*args)

    def fix_selected(self):
        sc = SignalContainer(app_node=self)
        for selected in self.get_selected():
            sc.segment_fixed(selected)
        sc.send()

    def unfix_selected(self):
        sc = SignalContainer(app_node=self)
        for selected in self.get_selected():
            sc.segment_unfixed(selected)
        sc.send()

    def fix_all(self):
        sc = SignalContainer(app_node=self)
        for roi in self.roi_dict.values():
            sc.segment_fixed(roi.parameters)
        sc.send()

    def unfix_all(self):
        sc = SignalContainer(app_node=self)
        for roi in self.roi_dict.values():
            sc.segment_unfixed(roi.parameters)
        sc.send()

    def delete_selected(self):
        sc = SignalContainer(app_node=self)
        for selected in self.get_selected():
            sc.segment_deleted(selected)
        sc.send()

    def select_all(self):
        sc = SignalContainer(app_node=self)
        keys = list(self.roi_dict.keys())
        sc.status_changed(StatusChangedContainer(keys, True, False))
        sc.send()

    def unselect_all(self):
        sc = SignalContainer(app_node=self)
        keys = list(self.roi_dict.keys())
        sc.status_changed(StatusChangedContainer(keys, False, False))
        sc.send()

    def change_roi_type(self, value: RoiParameters):
        self.on_type_changed(value)
        SignalContainer(app_node=self).type_changed(value).send()