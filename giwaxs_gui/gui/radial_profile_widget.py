# -*- coding: utf-8 -*-
import logging
from typing import List

import numpy as np
from scipy.signal import find_peaks
from scipy.optimize import curve_fit

from PyQt5.QtGui import QColor


from .basic_widgets import (BasicInputParametersWidget, ConfirmButton,
                            RoundedPushButton, Smooth1DPlot)
from .signal_connection import SignalConnector, SignalContainer
from .roi.roi_widgets import Roi1D
from .roi.roi_containers import BasicROIContainer

from ..config import read_config
from ..interpolation import get_radial_profile
from ..utils import Icon, RoiParameters, show_error

logger = logging.getLogger(__name__)


class RadialProfileWidget(BasicROIContainer, Smooth1DPlot):
    _DefaultRoiWidth = 50
    _DefaultNewRoiParameters = dict(radius=10, width=5)

    def __init__(self, signal_connector: SignalConnector,
                 parent=None):
        BasicROIContainer.__init__(self, signal_connector)
        Smooth1DPlot.__init__(self, parent)
        self.radial_profile = None
        self._peaks_setup = None
        self.x_axis = None
        self._fit_parameters_dict = read_config(PeaksSetupWindow.NAME)
        self.update_image()

    def __init_toolbars__(self):
        super().__init_toolbars__()

        fit_toolbar = self.addToolBar('Fitting')
        fit_toolbar.setStyleSheet('background-color: black;')

        find_peaks_widget = ConfirmButton(Icon('find'), text='Find peaks?')
        find_peaks_widget.label_widget.setStyleSheet(
            'QLabel { color : white ; }')
        find_peaks_widget.clicked.connect(self.find_peaks)
        fit_toolbar.addWidget(find_peaks_widget)

        fit_peaks_widget = ConfirmButton(Icon('fit'), text='Fit selected peaks?')
        fit_peaks_widget.label_widget.setStyleSheet(
            'QLabel { color : white ; }')
        fit_peaks_widget.clicked.connect(self.fit_selected)
        fit_toolbar.addWidget(fit_peaks_widget)

        setup_action = fit_toolbar.addAction(Icon('setup'), 'Fit setup')
        setup_action.triggered.connect(self.open_peaks_setup)

        segments_toolbar = self.addToolBar('Segments')
        segments_toolbar.setStyleSheet('background-color: black;')

        create_roi_widget = RoundedPushButton(
            icon=Icon('add'), radius=30)
        create_roi_widget.clicked.connect(self.emit_create_segment)
        segments_toolbar.addWidget(create_roi_widget)

        delete_selected_widget = ConfirmButton(
            Icon('delete'), text='Delete selected roi?')
        delete_selected_widget.clicked.connect(self.emit_delete_selected_roi)
        delete_selected_widget.label_widget.setStyleSheet(
            'QLabel { color : white ; }')

        segments_toolbar.addWidget(delete_selected_widget)
        fix_all = RoundedPushButton(icon=Icon('fix_all'), radius=120, background_color=QColor(0, 0, 0, 0))
        fix_all.setFixedWidth(60)
        fix_all.setFixedHeight(30)
        fix_all.clicked.connect(self.fix_all)
        segments_toolbar.addWidget(fix_all)
        unfix_all = RoundedPushButton(icon=Icon('unfix_all'), radius=120, background_color=QColor(0, 0, 0, 0))
        unfix_all.setFixedWidth(60)
        unfix_all.setFixedHeight(30)
        unfix_all.clicked.connect(self.unfix_all)
        segments_toolbar.addWidget(unfix_all)

    def process_signal(self, s: SignalContainer):
        update_image = False
        for _ in s.image_changed():
            update_image = True
        for _ in s.geometry_changed():
            update_image = True
        for _ in s.scale_changed():
            self.update_x_axis()
        BasicROIContainer.process_signal(self, s)
        if update_image:
            self.update_image()

    def find_peaks(self):
        # TODO show message if number of peaks exceeds max number and suggest to increase sigma.
        if self._fit_parameters_dict.get('sigma_find', None) is not None:
            self.set_sigma(self._fit_parameters_dict['sigma_find'])
        peaks = find_peaks(self.radial_profile)[0]
        sc = SignalContainer(app_node=self)
        for i, peak in enumerate(peaks):
            segment = RoiParameters(peak * self.image.scale, self._DefaultRoiWidth * self.image.scale,
                                    name=f'Proposed ring {i}')
            sc.segment_created(segment)
        sc.send()

    def fit_selected(self):
        if self._fit_parameters_dict.get('sigma_fit', None) is not None:
            self.set_sigma(self._fit_parameters_dict['sigma_fit'])
        sc = SignalContainer(app_node=self)
        fit_params = FitParameters(self.x_axis, self.radial_profile, self.image.scale)
        for value in self.get_selected():
            fit_params.add_value(value)
            value = list(fit_params.fit())[0]
            if value is not None:
                sc.segment_moved(value, signal_type='broadcast')
                sc.segment_fixed(value)
            fit_params.clear()
        sc.send()

    def fit_together(self):
        if self._fit_parameters_dict.get('sigma_fit', None) is not None:
            self.set_sigma(self._fit_parameters_dict['sigma_fit'])
        sc = SignalContainer(app_node=self)
        fit_params = FitParameters(self.x_axis, self.radial_profile, self.image.scale)
        fit_params.add_values(self.get_selected())
        for value in fit_params.fit():
            sc.segment_moved(value, signal_type='broadcast')
            sc.segment_fixed(value)
        sc.send()

    def _fit_many(self, value_list):
        pass

    def _fit_roi(self, value: RoiParameters):
        scale = self.image.scale
        mu_min, mu_max = value.radius - value.width / 2, value.radius + value.width / 2
        x1, x2 = (int(mu_min / scale),
                  int(mu_max / scale))
        data = self.radial_profile[x1:x2]
        x = self.x_axis[x1:x2]
        A = data.max()
        sigma = value.width / 2
        mu = value.radius
        B = 0
        try:
            res = curve_fit(gauss, x, data, (A, mu, sigma, B),
                            bounds=((0, mu_min, 0, 0),
                                    (A, mu_max, sigma * 2, A)))
            A, mu, sigma, B = res[0]
            return value._replace(radius=mu, width=sigma * 2,
                                  fit_r_parameters=(A, mu, sigma, B))
        except RuntimeError:
            return

    def _get_default_roi_parameters(self):
        scale = self.image.scale
        param_dict = self._DefaultNewRoiParameters.copy()
        param_dict['radius'] *= scale
        param_dict['width'] *= scale
        return RoiParameters(**param_dict)

    def open_peaks_setup(self):
        self._peaks_setup = PeaksSetupWindow()
        self._peaks_setup.apply_signal.connect(self.set_fit_parameters)
        self._peaks_setup.close_signal.connect(self.close_peaks_setup)
        self._peaks_setup.show()

    def set_fit_parameters(self, params: dict):
        self._fit_parameters_dict = params

    def close_peaks_setup(self):
        self._peaks_setup = None

    def emit_create_segment(self, *args):
        BasicROIContainer.emit_create_segment(
            self, self._get_default_roi_parameters()
        )

    def emit_delete_selected_roi(self):
        sc = SignalContainer()
        for roi in [roi for roi in self.roi_dict.values()
                    if roi.active]:
            sc.segment_deleted(roi)
        self.signal_connector.emit_upward(sc)

    def _get_roi(self, params: RoiParameters):
        return Roi1D(params)

    def _add_item(self, roi):
        self.centralWidget().plot_item.addItem(roi)

    def _remove_item(self, roi):
        self.centralWidget().plot_item.removeItem(roi)

    def update_image(self):
        if self.image.rr is None or self.image.image is None:
            return
        self.radial_profile = get_radial_profile(
            self.image.image, self.image.rr, self.sigma)
        self.update_x_axis()

    def update_x_axis(self, update_image: bool = True):
        rr = self.image.rr
        self.x_axis = np.linspace(rr.min(), rr.max(), self.radial_profile.size) * self.image.scale
        if update_image:
            self.centralWidget().set_data(self.x_axis, self.radial_profile)


class PeaksSetupWindow(BasicInputParametersWidget):
    P = BasicInputParametersWidget.InputParameters

    PARAMETER_TYPES = (P('max_peaks_number',
                         'Maximum number of peaks',
                         int, 'Do not recommended to put high numbers'),
                       P('init_width', 'Peaks width', float,
                         'Gaussian fitting will start with this number'),
                       P('sigma_find', 'Sigma to find peaks', float,
                         'Default sigma value for gaussian smooth\n'
                         'applied before initial peaks finding to\n'
                         'avoid noise peaks. To use current lambda, \n'
                         'leave empty.', True),
                       P('sigma_fit', 'Sigma to find peaks', float,
                         'Default sigma value for gaussian smooth\n'
                         'applied before gaussian fitting of \n'
                         'found peaks. To use current lambda, \n'
                         'leave empty.', True)
                       )

    NAME = 'Fitting parameters'


class FitParameters(object):
    _MAXIMUM_NUMBER_OF_PEAKS = 6

    @property
    def x(self):
        if self._x1 is None or self._x2 is None:
            return self._x
        else:
            return self._x[self._x1:self._x2]

    @property
    def y(self):
        if self._x1 is None or self._x2 is None:
            return self._y
        else:
            return self._y[self._x1:self._x2]

    @property
    def bounds(self):
        return tuple(self._lower_bounds), tuple(self._upper_bounds)

    @property
    def init_parameters(self):
        return tuple(self._init_conditions)

    def __init__(self, x, y, scale: float):
        self._x = x
        self._y = y
        self._scale = scale
        self._number_of_rois = 0
        self._upper_bounds = []
        self._lower_bounds = []
        self._init_conditions = []
        self._values = []
        self._x1 = None
        self._x2 = None

    def add_value(self, value: RoiParameters):
        mu_min, mu_max = value.radius - value.width / 2, value.radius + value.width / 2
        x1, x2 = (int(mu_min / self._scale),
                  int(mu_max / self._scale))
        data = self._y[x1:x2]
        if not data.size:
            return
        A = data.max()
        sigma = value.width / 2
        mu = value.radius
        B = 0
        self._init_conditions.extend([A, mu, sigma, B])
        self._lower_bounds.extend([0, mu_min, 0, 0])
        self._upper_bounds.extend([A, mu_max, sigma * 2, A])

        if self._x1 is None or self._x1 > x1:
            self._x1 = x1
        if self._x2 is None or self._x2 < x2:
            self._x2 = x2
        self._values.append(value)
        self._number_of_rois += 1

    def add_values(self, values: List[RoiParameters]):
        for value in values:
            self.add_value(value)

    def fit(self):
        if not self._number_of_rois:
            return ()
        elif self._number_of_rois > self._MAXIMUM_NUMBER_OF_PEAKS:
            show_error(f'The maximum number of peaks for this option is '
                       f'limited ({self._MAXIMUM_NUMBER_OF_PEAKS}). "Fit together" '
                       f'option is only necessary for overlapping peaks.',
                       'Maximum number of peaks exceeded')
            return ()
        elif self._number_of_rois == 1:
            func = gauss
        else:
            func = multi_gauss
        try:
            res = curve_fit(func, self.x, self.y, self.init_parameters,
                            bounds=self.bounds)
            parameters = res[0]
            for i, value in enumerate(self._values):
                A, mu, sigma, B = parameters[4 * i:(4 * i + 4)]
                yield value._replace(radius=mu, width=sigma * 2,
                                     fit_r_parameters=(A, mu, sigma, B))
        except RuntimeError:
            return ()

    def clear(self):
        self._number_of_rois = 0
        self._upper_bounds = []
        self._lower_bounds = []
        self._init_conditions = []
        self._values = []
        self._x1 = None
        self._x2 = None


def gauss(x, *p):
    A, mu, sigma, B = p
    return A * np.exp(-(x - mu) ** 2 / (2. * sigma ** 2)) + B


def multi_gauss(x, *p):
    if len(p) % 4:
        raise ValueError(f'Wrong number of parameters {len(p)}.')
    res = np.zeros_like(x)
    for i in range(len(p) // 4):
        res += gauss(x, *p[4 * i:(4 * i + 4)])
    return res
