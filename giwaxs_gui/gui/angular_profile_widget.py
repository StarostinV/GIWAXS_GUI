# -*- coding: utf-8 -*-
import logging

from .signal_connection import SignalContainer, SignalConnector, StatusChangedContainer
from .roi.roi_widgets import Roi1DAngular
from .roi.roi_containers import BasicROIContainer

from .basic_widgets import Smooth1DPlot
from ..utils import RoiParameters

logger = logging.getLogger(__name__)


class AngularProfileWidget(BasicROIContainer, Smooth1DPlot):
    def __init__(self, signal_connector: SignalConnector, parent=None):
        BasicROIContainer.__init__(self, signal_connector)
        Smooth1DPlot.__init__(self, parent)
        self._update_suggested = False
        self.current_roi_key = None
        self.bins_number = 300

    def process_signal(self, sc: SignalContainer):
        for signal in sc.segment_moved():
            if signal().key == self.current_roi_key:
                self.update_profile()
        BasicROIContainer.process_signal(self, sc)

    def _on_status_changed(self, sig: StatusChangedContainer):
        super()._on_status_changed(sig)
        selected_params = self.get_selected()
        if (
                len(selected_params) == 1 and
                self.current_roi_key != selected_params[0].key
        ):
            self._change_current_roi(selected_params[0].key)

    def _change_current_roi(self, k):
        self._remove_current_roi()
        self.current_roi_key = k
        self.roi_dict[self.current_roi_key].show()
        self.update_profile()

    def _remove_current_roi(self):
        if self.current_roi_key is not None:
            self.roi_dict[self.current_roi_key].hide()
            self.current_roi_key = None

    def _get_roi(self, params: RoiParameters):
        roi = Roi1DAngular(params)
        roi.hide()
        return roi

    def _add_item(self, roi):
        self.image_view.plot_item.addItem(roi)

    def _remove_item(self, roi):
        if roi.key == self.current_roi_key:
            self.current_roi_key = None
        self.image_view.plot_item.removeItem(roi)

    def update_profile(self):
        if any(x is None for x in
               (self.current_roi_key,
                self.image.phi,
                self.image.image,
                self.image.rr)):
            return
        roi = self.roi_dict[self.current_roi_key]
        r, w = roi.value.radius / self.image.scale, roi.value.width / self.image.scale
        r1, r2 = r - w / 2, r + w / 2
        self.x, self.y = self.image.get_angular_profile(r1, r2)
        self.plot()

    def send_value_changed(self, value: RoiParameters):
        # TODO: makes sense to switch to dependency injection scheme with one segments holder.
        sc = SignalContainer(app_node=self)
        if value.type == RoiParameters.roi_types.ring:
            value = value._replace(type=RoiParameters.roi_types.segment)
            self.roi_dict[value.key].parameters = value
            sc.type_changed(value)
        sc.segment_moved(value)
        sc.send()
