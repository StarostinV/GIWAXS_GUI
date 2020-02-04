# -*- coding: utf-8 -*-
import logging

from PyQt5.QtWidgets import QMainWindow

from .parameters_widget import InterpolateSetupWindow

from ..basic_widgets import CustomImageViewer, BlackToolBar
from ..roi.roi_widgets import Roi2DRect
from ..roi.roi_containers import AbstractROIContainer
from ..signal_connection import SignalConnector, SignalContainer

from ...utils import RoiParameters, Icon

logger = logging.getLogger(__name__)


class InterpolateImageWidget(AbstractROIContainer, QMainWindow):
    def __init__(self, signal_connector: SignalConnector,
                 parent=None):
        AbstractROIContainer.__init__(self, signal_connector)
        QMainWindow.__init__(self, parent)
        self._setup_window = None
        self._image_viewer = CustomImageViewer(self)
        self.setCentralWidget(self._image_viewer)
        self.__init_toolbar__()
        self.update_image()

    def process_signal(self, s: SignalContainer):
        super().process_signal(s)
        update_image = False
        if s.image_changed():
            update_image = True
        if s.geometry_changed_finish():
            update_image = True
        if s.transformation_added():
            update_image = True
        if update_image:
            self.update_image()

    def _on_scale_changed(self):
        self.set_axes()

    def _add_item(self, roi):
        if isinstance(roi, Roi2DRect):
            self._image_viewer.image_plot.addItem(roi)

    def _remove_item(self, roi):
        if isinstance(roi, Roi2DRect):
            self._image_viewer.image_plot.removeItem(roi)

    def _get_roi(self, params: RoiParameters):
        return Roi2DRect(params)

    def __init_toolbar__(self):
        setup_toolbar = BlackToolBar('Setup', self)
        self.addToolBar(setup_toolbar)

        setup_action = setup_toolbar.addAction(Icon('setup'), 'Setup')
        setup_action.triggered.connect(self.open_setup_window)

    def update_image(self):
        p_image = self.image.interpolate()
        if p_image is not None:
            roi_values = [value.parameters for value in self.roi_dict.values()]
            active_list = [value.active for value in self.roi_dict.values()]
            for p in roi_values:
                self.delete_roi(p)
            self.set_data(p_image)
            self.set_axes()
            for p, a in zip(roi_values, active_list):
                self.add_roi(p)
                if a:
                    self.roi_dict[p.key].set_active()

    def set_data(self, image):
        self._image_viewer.set_data(image)

    def set_axes(self):
        # TODO: fix bug when r_size and phi_size are different.
        r, p = self.image.interpolation.r_axis, self.image.interpolation.phi_axis
        r_min, r_max = r.min(), r.max()
        phi_min, phi_max = p.min(), p.max()

        aspect_ratio = (phi_max - phi_min) * p.size / (r_max - r_min) / r.size

        self._image_viewer.set_x_axis(r_min, r_max)
        self._image_viewer.set_y_axis(phi_min, phi_max)
        self._image_viewer.view_box.setAspectLocked(True, aspect_ratio)

    def open_setup_window(self):
        self._setup_window = InterpolateSetupWindow()
        self._setup_window.apply_signal.connect(self.set_parameters)
        self._setup_window.close_signal.connect(self.close_setup)
        self._setup_window.show()

    def set_parameters(self, params: dict):
        self.image.set_interpolation_parameters(params)
        self.update_image()

    def close_setup(self):
        self._setup_window = None
