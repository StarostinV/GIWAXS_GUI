# -*- coding: utf-8 -*-
import logging

import numpy as np
from scipy.ndimage import gaussian_filter1d

from PyQt5.QtWidgets import (QMainWindow, QFrame, QHBoxLayout)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

from pyqtgraph import GraphicsLayoutWidget
from .sliders import AnimatedSlider

logger = logging.getLogger(__name__)


class Custom1DPlot(GraphicsLayoutWidget):
    def __init__(self, *args, parent=None):
        super(Custom1DPlot, self).__init__(parent)
        self.plot_item = self.addPlot()
        self.plot_item.setMenuEnabled(False)
        self.plot = self.plot_item.plot(*args)

    def set_data(self, *args):
        self.plot.setData(*args)

    def clear_data(self):
        self.plot_item.clearPlots()

    def set_x(self, x):
        x = np.array(x)
        y = self.plot.yData
        if y.shape != x.shape:
            return
        self.plot.setData(x, y)


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
        param_toolbar = self.addToolBar('Parameters')
        param_toolbar.setStyleSheet('background-color: black;')

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
        self.image_view.set_data(self.x, self.smoothed_y)
