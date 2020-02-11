# -*- coding: utf-8 -*-
import logging
from enum import Enum
import weakref

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from scipy.ndimage import gaussian_filter1d

from PyQt5.QtWidgets import (QMainWindow, QWidget,
                             QFrame, QHBoxLayout,
                             QVBoxLayout, QPushButton,
                             QRadioButton)
from PyQt5.QtGui import QColor, QPen
from PyQt5.QtCore import Qt, pyqtSignal

from pyqtgraph import GraphicsLayoutWidget, LinearRegionItem
from .sliders import AnimatedSlider
from .toolbars import BlackToolBar
from ..basic_widgets import RoundedPushButton
from ...config import read_config, save_config
from ...utils import Icon, show_error

logger = logging.getLogger(__name__)


class Custom1DPlot(GraphicsLayoutWidget):
    def __init__(self, *args, parent=None, pen: QPen = None):
        super(Custom1DPlot, self).__init__(parent)
        self.plot_item = self.addPlot()
        self.plot_item.setMenuEnabled(False)
        self.plot = self.plot_item.plot(*args)
        pen = pen or self._default_pen()
        self.plot.setPen(pen)

    def set_data(self, *args):
        self.plot.setData(*args)

    def clear_plot(self):
        self.plot.clear()

    def set_x(self, x):
        x = np.array(x)
        y = self.plot.yData
        if y.shape != x.shape:
            return
        self.plot.setData(x, y)

    @staticmethod
    def _default_pen():
        pen = QPen(QColor('white'))
        pen.setStyle(Qt.SolidLine)
        pen.setWidth(3)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCosmetic(True)
        return pen


class Smooth1DPlot(QMainWindow):
    _MaximumSliderWidth = 200
    _MaximumSliderHeight = 30

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, value):
        self._y = value
        self.update_smoothed_y()

    @property
    def smoothed_y(self):
        return self._smoothed_y

    @property
    def x(self):
        if self._x is None and self._y is not None:
            return np.arange(self._y.size)
        else:
            return self._x

    @x.setter
    def x(self, value):
        self._x = value

    def update_smoothed_y(self):
        y = self.y
        if isinstance(y, np.ndarray):
            if self.sigma:
                self._smoothed_y = gaussian_filter1d(y, self.sigma)
            else:
                self._smoothed_y = y
        else:
            self._smoothed_y = None

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent=parent)
        self.image_view = Custom1DPlot()
        self.setCentralWidget(self.image_view)
        self.sigma = 0
        self._y = None
        self._smoothed_y = None
        self._x = None
        self.__init_toolbars__()

    def __init_toolbars__(self):
        param_toolbar = BlackToolBar('Parameters', self)
        self.addToolBar(param_toolbar)

        self.__init_sigma_slider__(param_toolbar)

    def __init_sigma_slider__(self, toolbar):
        sigma_slider = AnimatedSlider('𝞼', (0, 10), self.sigma,
                                      decimals=2)
        sigma_slider.setMaximumWidth(self._MaximumSliderWidth)
        sigma_slider.setMaximumHeight(self._MaximumSliderHeight)
        sigma_slider.valueChanged.connect(self.update_sigma)
        sigma_slider.setStyleSheet('background-color: white;')
        sigma_slider.shadow.setColor(QColor('blue'))
        self.sigma_slider = sigma_slider
        frame = QFrame()
        layout = QHBoxLayout()
        frame.setLayout(layout)
        frame.setGeometry(0, 0, self._MaximumSliderWidth, toolbar.height() * 0.9)
        layout.addWidget(sigma_slider, alignment=Qt.AlignHCenter)
        toolbar.addWidget(frame)

    def set_sigma(self, value: float):
        self.update_sigma(value)
        self.sigma_slider.set_value(value, change_bounds=True)

    def update_sigma(self, value: float):
        self.sigma = value
        self.update_smoothed_y()
        self.plot()

    def plot(self):
        if self.x is not None and self.smoothed_y is not None:
            self.image_view.set_data(self.x, self.smoothed_y)
            self.image_view.plot_item.autoRange()

    def clear_plot(self):
        self.image_view.clear_plot()


class PlotWithBaseLineCorrection(Smooth1DPlot):
    @property
    def baseline_curve(self):
        if self._baseline.status == BaseLineStatus.baseline_subtracted:
            return self._baseline.baseline

    @Smooth1DPlot.y.setter
    def y(self, value):
        self._baseline.clear()
        Smooth1DPlot.y.fset(self, value)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._baseline = BaseLine(self)

    def __init_toolbars__(self):
        super().__init_toolbars__()

        baseline_toolbar = BlackToolBar('Baseline Correction')
        self.addToolBar(baseline_toolbar)

        baseline_button = RoundedPushButton(parent=baseline_toolbar, icon=Icon('baseline'),
                                            radius=30)
        baseline_button.clicked.connect(self.open_baseline_setup)
        baseline_toolbar.addWidget(baseline_button)

    def update_smoothed_y(self):
        super().update_smoothed_y()
        if (
                self.baseline_curve is not None and
                self._baseline.baseline.size == self._y.size
        ):
            self._smoothed_y = self._smoothed_y - self.baseline_curve

    def open_baseline_setup(self):
        if self.y is not None:
            self._baseline.open_setup()


class BaseLine(object):
    @property
    def status(self):
        return self._status

    @property
    def roi(self):
        return self._roi

    @property
    def baseline(self):
        if self._status == BaseLineStatus.baseline_subtracted:
            return self._baseline
        else:
            return

    @property
    def parent(self):
        return self._parent()

    def __init__(self, parent: PlotWithBaseLineCorrection):
        self._parent = weakref.ref(parent)
        self._baseline = None
        self._x_axis = None
        self._x1 = None
        self._x2 = None
        self._smoothness_param = None
        self._asymmetry_param = None
        self._baseline_setup_widget = None
        self.baseline_plot = None
        self._status = BaseLineStatus.no_baseline
        self.__init_parameters__()
        self.__init_roi__()

    def clear(self):
        self._baseline = None
        self._set_status(BaseLineStatus.no_baseline)
        self._remove_baseline_from_plot()

    def open_setup(self):
        self.set_axis(self.parent.x)
        self._baseline_setup_widget = setup = BaseLineSetup(self._status, **self.get_parameters())
        if None in (self._x1, self._x2):
            self.set_default_bounds()
        self.roi.show()
        setup.calculate_signal.connect(self._on_calculate_baseline)
        setup.subtract_signal.connect(self._on_subtracting_baseline)
        setup.restore_signal.connect(self._on_restoring_data)
        setup.close_signal.connect(self._on_closing_setup)
        setup.show()

    def _set_status(self, status: 'BaseLineStatus'):
        self._status = status
        if self._baseline_setup_widget:
            self._baseline_setup_widget.set_status(status)

    def _on_calculate_baseline(self, params: dict):
        self.set_parameters(**params)
        self.update_bounds()
        try:
            self.get_baseline_correction(self.parent.smoothed_y)
        except Exception as err:
            logger.exception(err)
            show_error('Failed calculating baseline. Change roi region or parameters and try again.',
                       'Baseline calculation error')
        self._plot_baseline()
        self._set_status(BaseLineStatus.baseline_calculated)

    def _on_subtracting_baseline(self):
        self._remove_baseline_from_plot()
        self._set_status(BaseLineStatus.baseline_subtracted)
        self.parent.update_smoothed_y()
        self.parent.plot()

    def _on_restoring_data(self):
        self._set_status(BaseLineStatus.baseline_restored)
        self._plot_baseline()
        self.parent.update_smoothed_y()
        self.parent.plot()

    def _on_closing_setup(self):
        self._baseline_setup_widget = None
        self.roi.hide()
        if (self.status == BaseLineStatus.baseline_calculated or
                self.status == BaseLineStatus.baseline_restored):
            self._remove_baseline_from_plot()
            self.clear()

    def _plot_baseline(self):
        if not self.baseline_plot:
            self.baseline_plot = self.parent.image_view.plot_item.plot()
        pen = QPen(QColor('red'))
        pen.setStyle(Qt.DashDotLine)
        pen.setWidth(4)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCosmetic(True)
        self.baseline_plot.setData(self._x_axis, self._baseline, pen=pen)

    def _remove_baseline_from_plot(self):
        if self.baseline_plot:
            self.parent.image_view.plot_item.removeItem(self.baseline_plot)
            self.baseline_plot = None

    def __init_parameters__(self):
        # not necessary
        params = read_config('Baseline correction')
        self.set_parameters(**params)

    def __init_roi__(self):
        self._roi = LinearRegionItem()
        self._roi.hide()
        self._roi.setBrush(QColor(255, 255, 255, 50))
        self.parent.image_view.plot_item.addItem(self.roi)

    def update_bounds(self):
        self._x1, self._x2 = self.roi.getRegion()

    def set_parameters(self, **kwargs):
        if 'smoothness_param' in kwargs:
            self._smoothness_param = kwargs['smoothness_param']
        if 'asymmetry_param' in kwargs:
            self._asymmetry_param = kwargs['asymmetry_param']

    def get_parameters(self):
        params = dict()
        if self._asymmetry_param is not None:
            params['asymmetry_param'] = self._asymmetry_param
        if self._smoothness_param is not None:
            params['smoothness_param'] = self._smoothness_param
        return params

    def set_axis(self, x: np.ndarray):
        self._x_axis = x
        self.set_default_bounds()

    def set_bounds(self, x1: float, x2: float):
        self._x1, self._x2 = x1, x2
        self.roi.setRegion((x1, x2))

    def set_default_bounds(self):
        if self._x_axis is None:
            self.set_bounds(0, 1)
        else:
            self.set_bounds(self._x_axis.min(), self._x_axis.max())

    def get_baseline_correction(self, y: np.ndarray):
        if (
                self._x_axis is None or
                y.size != self._x_axis.size or
                None in (self._x1, self._x2,
                         self._smoothness_param,
                         self._asymmetry_param)
        ):
            return
        x1, x2 = self._get_coords()
        baseline = baseline_correction(y[x1:x2], self._smoothness_param, self._asymmetry_param)
        self._baseline = np.zeros_like(y)
        self._baseline[x1:x2] = baseline
        return self.baseline

    def _get_coords(self):
        scale_factor = self._x_axis.size / (self._x_axis.max() - self._x_axis.min())
        x_min = self._x_axis.min()
        min_ind, max_ind = 0, self._x_axis.size
        x1 = int((self._x1 - x_min) * scale_factor)
        x2 = int((self._x2 - x_min) * scale_factor)
        x1 = min((max((x1, min_ind)), max_ind))
        x2 = min((max((x2, min_ind)), max_ind))
        xs = (x1, x2)
        return min(xs), max(xs)


class BaseLineStatus(Enum):
    no_baseline = 1
    baseline_calculated = 2
    baseline_restored = 2
    baseline_subtracted = 3


class BaseLineSetup(QWidget):
    calculate_signal = pyqtSignal(dict)
    subtract_signal = pyqtSignal()
    restore_signal = pyqtSignal()
    close_signal = pyqtSignal()

    NAME = 'Baseline correction'

    def __init__(self, status: BaseLineStatus, **current_parameters):
        super().__init__()
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
        self.setWindowTitle(self.NAME)
        self.setWindowIcon(Icon('baseline'))
        self._status = None
        self.__init_ui__(current_parameters)
        self.set_status(status)

    def __init_ui__(self, current_parameters: dict = None):
        layout = QVBoxLayout(self)
        if not current_parameters:
            current_parameters = read_config(self.NAME)
        smoothness_param = current_parameters.get('smoothness_param', 100)
        asymmetry_param = current_parameters.get('asymmetry_param', 0.01)

        self.smoothness_slider = AnimatedSlider('Smoothness parameter', (1e2, 1e4), smoothness_param,
                                                self, Qt.Horizontal, disable_changing_status=True, decimals=3)

        self.asymmetry_slider = AnimatedSlider('Asymmetry parameter', (0.001, 0.1), asymmetry_param,
                                               self, Qt.Horizontal, disable_changing_status=True, decimals=3)

        self.save_params_box = QRadioButton('Save as default')
        self.save_params_box.setChecked(True)
        self.calculate_button = QPushButton('Calculate baseline')
        self.calculate_button.clicked.connect(self.emit_calculate)
        self.subtract_button = QPushButton('Subtract baseline')
        self.subtract_button.clicked.connect(self.subtract_signal.emit)
        self.restore_button = QPushButton('Restore line')
        self.restore_button.clicked.connect(self.restore_signal.emit)

        layout.addWidget(self.smoothness_slider)
        layout.addWidget(self.asymmetry_slider)
        layout.addWidget(self.save_params_box)
        layout.addWidget(self.calculate_button)
        layout.addWidget(self.subtract_button)
        layout.addWidget(self.restore_button)

    def set_status(self, status: BaseLineStatus):
        if status == BaseLineStatus.no_baseline:
            self.calculate_button.setEnabled(True)
            self.subtract_button.setEnabled(False)
            self.restore_button.setEnabled(False)
        elif status == BaseLineStatus.baseline_calculated:
            self.subtract_button.setEnabled(True)
            self.restore_button.setEnabled(False)
            self.calculate_button.setEnabled(True)
        elif status == BaseLineStatus.baseline_subtracted:
            self.subtract_button.setEnabled(False)
            self.restore_button.setEnabled(True)
            self.calculate_button.setEnabled(False)
        else:
            logger.error(f'Unknown status {status}')
            return
        self._status = status

    def get_params_dict(self):
        return dict(smoothness_param=self.smoothness_slider.value,
                    asymmetry_param=self.asymmetry_slider.value)

    def emit_calculate(self):
        self.calculate_signal.emit(self.get_params_dict())

    def closeEvent(self, a0) -> None:
        if self.save_params_box.isChecked():
            save_config(self.NAME, self.get_params_dict())
        self.close_signal.emit()
        super().closeEvent(a0)


def baseline_correction(y: np.ndarray,
                        smoothness_param: float,
                        asymmetry_param: float,
                        max_niter: int = 1000):
    y_size = y.size
    laplacian = sparse.diags([1, -2, 1], [0, -1, -2], shape=(y_size, y_size - 2))
    laplacian_matrix = laplacian.dot(laplacian.transpose())

    z = np.zeros_like(y)
    w = np.ones(y_size)
    for i in range(max_niter):
        W = sparse.spdiags(w, 0, y_size, y_size)
        Z = W + smoothness_param * laplacian_matrix
        z = spsolve(Z, w * y)
        w_new = asymmetry_param * (y > z) + (1 - asymmetry_param) * (y < z)
        if np.allclose(w, w_new):
            break
        w = w_new
    else:
        logger.info(f'Solution has not converged, max number of iterations reached.')
    return z
