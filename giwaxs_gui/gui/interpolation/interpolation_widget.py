# -*- coding: utf-8 -*-
import logging

from PyQt5.QtWidgets import QMainWindow, QAction

from .parameters_widget import InterpolateSetupWindow

from ..basic_widgets import CustomImageViewer
from ..roi.roi_widgets import EmptyROI, Roi2DRect
from ..roi.roi_containers import AbstractROIContainer
from ..signal_connection import SignalConnector, SignalContainer

from ...utils import RoiParameters, Icon

logger = logging.getLogger(__name__)


# TODO: fix bug with scaling

# TODO: fix bug with negative angles

# TODO: add axes


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
        if s.image_changed():
            self.update_image()
        if s.geometry_changed_finish():
            self.update_image()

    def _add_item(self, roi):
        if isinstance(roi, Roi2DRect):
            self._image_viewer.image_plot.addItem(roi)

    def _remove_item(self, roi):
        if isinstance(roi, Roi2DRect):
            self._image_viewer.image_plot.removeItem(roi)

    def _get_roi(self, params: RoiParameters):
        r_size, phi_size = (self.image.interpolation.r_size,
                            self.image.interpolation.phi_size)
        image, rr, phi = self.image.image, self.image.rr, self.image.phi
        if any(x is None for x in (r_size, phi_size, image, rr, phi)):
            return EmptyROI(params)
        return Roi2DRect(params, rr, r_size, phi, phi_size)

    def __init_toolbar__(self):

        setup_toolbar = self.addToolBar('Setup')
        setup_toolbar.setStyleSheet('background-color: black;')

        setup_action = setup_toolbar.addAction(Icon('setup'), 'Setup')
        setup_action.triggered.connect(self.open_setup_window)

    def update_image(self):
        p_image = self.image.interpolate()
        if p_image is not None:
            roi_values = [value.parameters for value in self.roi_dict.values()]
            for p in roi_values:
                self.delete_roi(p)
            self.set_data(p_image)
            for p in roi_values:
                self.add_roi(p)

    def set_data(self, image):
        self._image_viewer.set_data(image)

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
