# -*- coding: utf-8 -*-
import logging

from PyQt5.QtWidgets import QMainWindow, QAction

from .basic_widgets import CustomImageViewer, BasicInputParametersWidget
from .roi_widgets import AbstractROIContainer, Roi2DRect, EmptyROI
from .signal_connection import SignalConnector, SignalContainer
from ..utils import RoiParameters, Icon
from ..interpolation import convert_image

logger = logging.getLogger(__name__)


class InterpolateImageWidget(AbstractROIContainer, QMainWindow):
    def __init__(self, signal_connector: SignalConnector,
                 parent=None):
        AbstractROIContainer.__init__(self, signal_connector)
        QMainWindow.__init__(self, parent)
        self._setup_window = None
        self._interpolation_parameters = InterpolateSetupWindow.current_default_values()
        self.setCentralWidget(CustomImageViewer(self))
        self.__init_toolbar__()
        self.update_image()

    def process_signal(self, s: SignalContainer):
        AbstractROIContainer.process_signal(self, s)

    def _add_item(self, roi):
        if isinstance(roi, Roi2DRect):
            self.centralWidget().image_plot.addItem(roi)

    def _remove_item(self, roi):
        if isinstance(roi, Roi2DRect):
            self.centralWidget().image_plot.removeItem(roi)

    def _get_roi(self, params: RoiParameters):
        if (self.image.image is None or
                self.image.rr is None or self.image.phi is None):
            return EmptyROI(params)
        return Roi2DRect(params,
                         self.image.rr, self._interpolation_parameters['r_size'],
                         self.image.phi, self._interpolation_parameters['phi_size'])

    def __init_toolbar__(self):
        toolbar = self.addToolBar('Main')
        toolbar.setStyleSheet('background-color: black;')

        update_action = QAction(Icon('update'), 'Update', self)
        update_action.triggered.connect(self.update_image)
        toolbar.addAction(update_action)

        setup_toolbar = self.addToolBar('Setup')
        setup_toolbar.setStyleSheet('background-color: black;')

        setup_action = setup_toolbar.addAction(Icon('setup'), 'Setup')
        setup_action.triggered.connect(self.open_setup_window)

    def update_image(self):
        image = self.image.image
        rr, phi = self.image.rr, self.image.phi
        if image is not None and rr is not None and phi is not None:
            roi_values = [value.parameters for value in self.roi_dict.values()]
            for p in roi_values:
                self.delete_roi(p)
            logger.info(f'Calculating interpolation ...')
            p_image = convert_image(image, rr, phi,
                                    self._interpolation_parameters['r_size'],
                                    self._interpolation_parameters['phi_size'],
                                    self._interpolation_parameters['r_window'],
                                    self._interpolation_parameters['phi_window'])
            logger.info(f'Interpolation is calculated.')
            self.set_data(p_image)
            for p in roi_values:
                self.add_roi(p)

    def set_data(self, image):
        self.centralWidget().set_data(image)

    def open_setup_window(self):
        self._setup_window = InterpolateSetupWindow()
        self._setup_window.apply_signal.connect(self.set_parameters)
        self._setup_window.close_signal.connect(self.close_setup)
        self._setup_window.show()

    def set_parameters(self, params: dict):
        self._interpolation_parameters = params

    def close_setup(self):
        self._setup_window = None


class InterpolateSetupWindow(BasicInputParametersWidget):
    P = BasicInputParametersWidget.InputParameters

    DEFAULT_DICT = dict(r_size=512, phi_size=512,
                        r_window=0.5, phi_window=0.5)

    PARAMETER_TYPES = (P('r_size',
                         'Radius size',
                         int),
                       P('phi_size', 'Angle size', int),
                       P('r_window', 'Radius averaging window', float),
                       P('phi_window', 'Phi averaging window', float))

    JSON_FILENAME = 'interpolation_parameters.json'

    @staticmethod
    def current_default_values():
        return InterpolateSetupWindow.get_default_values(InterpolateSetupWindow)
