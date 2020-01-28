# -*- coding: utf-8 -*-
import logging

import numpy as np
from scipy.ndimage import gaussian_filter1d

from .signal_connection import SignalContainer, SignalConnector, StatusChangedContainer
from .roi.roi_widgets import Roi1DAngular
from .roi.roi_containers import BasicROIContainer

from .basic_widgets import Smooth1DPlot
from ..utils import RoiParameters, Icon

logger = logging.getLogger(__name__)


class AngularProfileWidget(BasicROIContainer, Smooth1DPlot):
    def __init__(self, signal_connector: SignalConnector, parent=None):
        BasicROIContainer.__init__(self, signal_connector)
        Smooth1DPlot.__init__(self, parent)
        self.angular_profile = None
        self.x = None
        self._update_suggested = False
        self.current_roi_key = None
        self.bins_number = 300

    def __init_toolbars__(self):
        toolbar = self.addToolBar('Update')
        toolbar.setStyleSheet('background-color: black;')
        self.update_action = toolbar.addAction(Icon('update'), 'Update')
        self.update_action.triggered.connect(self.update_image)
        super().__init_toolbars__()

    def process_signal(self, sc: SignalContainer):
        for _ in sc.geometry_changed():
            self.update_x()
        for signal in sc.segment_moved():
            if signal().key == self.current_roi_key:
                self._suggest_update()
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
        self._suggest_update()

    def _remove_current_roi(self):
        if self.current_roi_key is not None:
            self.roi_dict[self.current_roi_key].hide()
            self.current_roi_key = None

    def _get_roi(self, params: RoiParameters):
        roi = Roi1DAngular(params)
        roi.hide()
        return roi

    def _add_item(self, roi):
        self.centralWidget().plot_item.addItem(roi)

    def _remove_item(self, roi):
        if roi.key == self.current_roi_key:
            self.current_roi_key = None
        self.centralWidget().plot_item.removeItem(roi)

    def update_x(self):
        if self.image.phi is not None:
            self.x = np.linspace(
                self.image.phi.min() * 180 / np.pi, self.image.phi.max() * 180 / np.pi,
                self.bins_number)

    def _suggest_update(self, suggest: bool = True):
        if self._update_suggested == suggest:
            return
        self._update_suggested = suggest
        if suggest:
            self.update_action.setIcon(Icon('update_suggested'))
        else:
            self.update_action.setIcon(Icon('update'))

    def update_sigma(self, value: float):
        self.sigma = value
        self._suggest_update()

    def update_image(self):
        if (
                self.current_roi_key is None or
                self.image.phi is None or
                self.image.image is None or
                self.image.rr is None or
                self.x is None
        ):
            return
        roi = self.roi_dict[self.current_roi_key]
        r, w = roi.value.radius / self.image.scale, roi.value.width / self.image.scale
        r1, r2 = r - w / 2, r + w / 2
        self.angular_profile = get_angular_profile(
            self.image.image.copy(), self.image.phi, self.image.rr, r1, r2, self.sigma,
            self.bins_number)
        self.centralWidget().set_data(self.x, self.angular_profile)
        self._suggest_update(False)

    def send_value_changed(self, value: RoiParameters):
        # TODO: makes sense to switch to dependency injection scheme with one segments holder.
        sc = SignalContainer(app_node=self)
        if value.type == RoiParameters.roi_types.ring:
            value = value._replace(type=RoiParameters.roi_types.segment)
            self.roi_dict[value.key].parameters = value
            sc.type_changed(value)
        sc.segment_moved(value)
        sc.send()


def get_angular_profile(image: np.array, phi: np.array, rr: np.array,
                        r1: float, r2: float, sigma: float = 0, bins_number: int = 500):
    assert image.shape == phi.shape == rr.shape
    logger.debug(f'calculating angular profile')
    phi_array = np.linspace(phi.min(), phi.max(), bins_number + 1)[1:]
    mask = (rr < r1) | (rr > r2)
    image[mask] = 0

    angular_profile = np.empty(bins_number)
    p1 = 0
    for i, p2 in enumerate(phi_array):
        angular_profile[i] = image[(phi > p1) & (phi < p2)].sum()
        p1 = p2
    if sigma:
        angular_profile = gaussian_filter1d(angular_profile, sigma)
    logger.debug(f'Angular profile is calculated.')
    return angular_profile
