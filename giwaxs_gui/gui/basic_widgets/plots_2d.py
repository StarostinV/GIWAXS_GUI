# -*- coding: utf-8 -*-
import logging

import numpy as np

from pyqtgraph import (GraphicsLayoutWidget, setConfigOptions,
                       ImageItem, HistogramLUTItem)

logger = logging.getLogger(__name__)


class CustomImageViewer(GraphicsLayoutWidget):
    @property
    def view_box(self):
        return self.image_plot.vb

    def __init__(self, parent=None, **kwargs):
        setConfigOptions(imageAxisOrder='row-major')
        super(CustomImageViewer, self).__init__(parent)
        self._scale = (1., 1.)
        self._center = (0, 0)

        self.__init_ui__()

    def __init_ui__(self):
        self.setWindowTitle('Image Viewer')
        self.image_plot = self.addPlot()
        self.image_plot.vb.setAspectLocked()
        self.image_plot.vb.invertY()
        self.image_item = ImageItem()
        self.image_plot.addItem(self.image_item)
        self.hist = HistogramLUTItem()
        self.hist.setImageItem(self.image_item)
        self.addItem(self.hist)

    def set_data(self, data, change_limits: bool = True, reset_axes: bool = False):
        if data is None:
            return
        self.image_item.setImage(data, change_limits)
        if change_limits:
            self.hist.setLevels(data.min(), data.max())
        if reset_axes:
            self.image_item.resetTransform()
        self.set_default_range()

    def set_default_range(self):
        axes = self.get_axes()
        self.image_plot.setRange(xRange=axes[0], yRange=axes[1])

    def set_auto_range(self):
        self.image_plot.autoRange()

    def set_levels(self, levels=None):
        if levels:
            self.hist.setLevels(levels[0], levels[1])
        else:
            self.hist.setLevels(self.image_item.image.min(),
                                self.image_item.image.max())

    def get_levels(self):
        return self.hist.getLevels()

    def set_center(self, center: tuple, pixel_units: bool = True):
        if not pixel_units:
            scale = self.get_scale()
            center = (center[0] / scale[0], center[1] / scale[1])
        if self._center != (0, 0) or self._scale != (1., 1.):
            self.image_item.resetTransform()
            self.image_item.scale(*self._scale)
        self.image_item.translate(- center[0], - center[1])
        self._center = center
        self.set_default_range()

    def set_scale(self, scale: float or tuple):
        if isinstance(scale, float) or isinstance(scale, int):
            scale = (scale, scale)
        if self._center != (0, 0) or self._scale != (1., 1.):
            self.image_item.resetTransform()
        self.image_item.scale(*scale)
        if self._center != (0, 0):
            self.image_item.translate(- self._center[0], - self._center[1])
        self._scale = scale
        self.set_default_range()

    def get_scale(self):
        # scale property is occupied by Qt superclass.
        return self._scale

    def get_center(self):
        return self._center

    def set_x_axis(self, x_min, x_max):
        self._set_axis(x_min, x_max, 0)
        self.set_default_range()

    def set_y_axis(self, y_min, y_max):
        self._set_axis(y_min, y_max, 1)
        self.set_default_range()

    def _set_axis(self, min_: float, max_: float, axis_ind: int):
        shape = self.image_item.image.shape
        scale = np.array(self._scale)
        scale[axis_ind] = (max_ - min_) / shape[axis_ind]
        center = np.array(self._center)
        center[axis_ind] = - min_ / scale[axis_ind]
        if self._center != (0, 0) or self._scale != (1., 1.):
            self.image_item.resetTransform()
        self.image_item.scale(scale[0], scale[1])
        self.image_item.translate(- center[0], - center[1])
        self._scale = tuple(scale)
        self._center = tuple(center)

    def get_axes(self):
        shape = np.array(self.image_item.image.shape)
        scale = np.array(self._scale)
        min_ = - np.array(self._center) * scale
        max_ = min_ + shape * scale
        return (min_[0], max_[0]), (min_[1], max_[1])
