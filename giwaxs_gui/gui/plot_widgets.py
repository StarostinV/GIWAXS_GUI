# -*- coding: utf-8 -*-
import logging

import numpy as np

from pyqtgraph import CircleROI, LineSegmentROI
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout)
from PyQt5.QtCore import pyqtSignal, Qt

from .basic_widgets import CustomImageViewer, AnimatedSlider
from .signal_connection import SignalConnector, SignalContainer, AppNode
from .roi.roi_widgets import Roi2DRing
from .roi.roi_containers import AbstractROIContainer
from ..utils import Icon, center_widget, RoiParameters

logger = logging.getLogger(__name__)


class GiwaxsImageViewer(AbstractROIContainer, CustomImageViewer):
    @property
    def beam_center(self):
        return self.image.beam_center

    class BeamCenterRoi(CircleROI):
        _ROI_SIZE = 200

        def __init__(self, beam_center, parent):
            CircleROI.__init__(self, (beam_center[1], beam_center[0]),
                               self._ROI_SIZE, movable=False, parent=parent)
            self._center = None
            self.set_center(beam_center)

        def set_center(self, value: tuple, y=None, update=True, finish=True, ):
            self._center = value
            radius = self.size().x() / 2
            pos = (value[1] - radius, value[0] - radius)
            super(GiwaxsImageViewer.BeamCenterRoi, self).setPos(
                pos, y, update, finish)

        def set_size(self, size: float):
            self.setSize((size, size), update=False, finish=False)
            self.set_center(self._center)

        def set_scale(self, scale: float):
            size = self._ROI_SIZE * scale
            self.set_size(size)

    class ZeroAngleRoi(LineSegmentROI):
        _ROI_SIZE = 300

        def __init__(self, beam_center, zero_angle, invert_angle, parent):
            self.beam_center = beam_center
            self.zero_angle = 0
            self.invert_angle = invert_angle

            self.coords = self.beam_center, self._get_second_point_coordinates()
            LineSegmentROI.__init__(self, self.coords, parent=parent, movable=False)
            self.handles[0]['item'].mouseDragEvent = lambda *args: None
            self.handles[0]['item'].mouseClickEvent = lambda *args: None
            self.handles[1]['item'].mouseDragEvent = lambda *args: None
            self.handles[1]['item'].mouseClickEvent = lambda *args: None

            self.set_center(self.beam_center)
            self.set_angle(zero_angle)
            self.hide()

        def _get_second_point_coordinates(self):
            angle = self.zero_angle
            if self.invert_angle:
                angle *= -1
            x = self.beam_center[1] + np.cos(angle * np.pi / 180) * self._ROI_SIZE
            y = self.beam_center[0] + np.sin(angle * np.pi / 180) * self._ROI_SIZE
            return x, y

        def set_center(self, value):
            self.beam_center = value
            self.setPos((value[1], value[0]))

        def set_angle(self, value):
            if self.invert_angle:
                value *= -1
            self._set_angle(value)

        def _set_angle(self, angle):
            diff_angle, self.zero_angle = angle - self.zero_angle, angle
            self.rotate(diff_angle)

        def set_invert(self, value):
            if value != self.invert_angle:
                self.invert_angle = value
                self._set_angle(-self.zero_angle)

    def __init__(self, signal_connector: SignalConnector,
                 parent=None, **kwargs):
        AbstractROIContainer.__init__(self, signal_connector)
        CustomImageViewer.__init__(self, parent, **kwargs)

        self._geometry_params_widget = None
        self.hist.sigLevelChangeFinished.connect(self._on_limits_changed)
        self.__init_center_roi__()

    def process_signal(self, s: SignalContainer):
        AbstractROIContainer.process_signal(self, s)
        for _ in s.image_changed():
            self.set_data(self.image.image, change_limits=False)
            self.set_levels(self.image.intensity_limits)
        for _ in s.transformation_added():
            self.set_data(self.image.image, change_limits=False)
        for _ in s.geometry_changed():
            self.update_beam_center(self.image.beam_center, emit_value=False)
        for _ in s.scale_changed():
            self._on_scale_changed()

    def _on_limits_changed(self):
        levels = self.get_levels()
        if levels != (0, 1):
            self.set_image_limits(self.get_levels())

    def _on_scale_changed(self):
        scale = self.image.scale
        self.set_scale(scale)
        self.center_roi.set_scale(scale)

    def _get_roi(self, params: RoiParameters):
        return Roi2DRing(params)

    def _add_item(self, roi):
        self.image_plot.addItem(roi)

    def _remove_item(self, roi):
        self.image_plot.removeItem(roi)

    def __init_center_roi__(self):
        self.center_roi = self.BeamCenterRoi(self.beam_center, parent=self.image_item)
        self.center_roi.setZValue(10)
        self.image_plot.addItem(self.center_roi)

        self.angle_roi = self.ZeroAngleRoi(self.beam_center, 0, False, self.image_item)
        self.angle_roi.setZValue(10)
        self.image_plot.addItem(self.angle_roi)

    def open_geometry_parameters(self):

        logger.debug(self._geometry_params_widget)
        if self.image.image is not None and self._geometry_params_widget is None:
            self._geometry_params_widget = GeometryParametersWidget(
                self.image.shape, self.beam_center, scale=self.image.scale)
            self._geometry_params_widget.change_center.connect(
                self.update_beam_center)
            self._geometry_params_widget.change_zero_angle.connect(self.set_zero_angle)
            self._geometry_params_widget.change_invert_angle.connect(self.set_invert_angle)
            self._geometry_params_widget.scale_changed.connect(self.emit_scale_changed)
            self._geometry_params_widget.close_event.connect(self.on_closing_beam_center_widget)

    def on_closing_beam_center_widget(self):
        self._geometry_params_widget = None

    def emit_scale_changed(self, value):
        self.image.set_scale(value)
        SignalContainer(app_node=self).scale_changed(0).send()

    def set_zero_angle(self, value):
        self.angle_roi.set_angle(value)

    def set_invert_angle(self, value):
        self.angle_roi.set_invert(value)

    def update_beam_center(self, value, emit_value: bool = True):
        if emit_value:
            self.set_beam_center(value)
        self.set_center((value[1], value[0]), pixel_units=True)


class GeometryParametersWidget(QWidget):
    change_center = pyqtSignal(list)
    change_zero_angle = pyqtSignal(float)
    change_invert_angle = pyqtSignal(bool)
    scale_changed = pyqtSignal(float)

    close_event = pyqtSignal()

    def __init__(self, image_shape: tuple,
                 beam_center: tuple, zero_angle: float = 0,
                 angle_direction: bool = True, scale: float = 1):
        super(GeometryParametersWidget, self).__init__(None, Qt.WindowStaysOnTopHint)
        self.beam_center = list(beam_center)
        self.image_shape = image_shape
        self.zero_angle = zero_angle
        self.scale = scale
        self.angle_direction = angle_direction
        self.__init__ui__()
        self.setWindowTitle('Set beam center coordinates')
        self.setWindowIcon(Icon('setup'))
        center_widget(self)
        self.show()

    def closeEvent(self, a0) -> None:
        self.close_event.emit()
        QWidget.closeEvent(self, a0)

    def __init__ui__(self):
        layout = QVBoxLayout(self)

        self.x_slider = AnimatedSlider('X center', (0, self.image_shape[1]),
                                       self.beam_center[1], self,
                                       Qt.Horizontal, disable_changing_status=True)
        self.x_slider.valueChanged.connect(self._connect_func(1))

        self.y_slider = AnimatedSlider('Y center', (0, self.image_shape[0]),
                                       self.beam_center[0], self,
                                       Qt.Horizontal, disable_changing_status=True)
        self.y_slider.valueChanged.connect(self._connect_func(0))

        # self.angle_slider = AnimatedSlider('Zero angle', (0, 360),
        #                                    self.zero_angle, self,
        #                                    Qt.Horizontal, disable_changing_status=True)
        # self.angle_slider.valueChanged.connect(self._connect_func(2))
        #
        # self.invert_angle_box = QCheckBox('Invert angle')
        # self.invert_angle_box.toggled.connect(self._connect_func(3))

        self.scale_edit = AnimatedSlider('Q to pixel ratio', (1e-10, 10),
                                         self.scale, self,
                                         Qt.Horizontal, disable_changing_status=True,
                                         decimals=5)
        self.scale_edit.valueChanged.connect(self.on_scale_changed)

        layout.addWidget(self.x_slider)
        layout.addWidget(self.y_slider)
        layout.addWidget(self.scale_edit)
        # layout.addWidget(self.angle_slider)
        # layout.addWidget(self.invert_angle_box)

    def on_scale_changed(self, value):
        self.scale = value
        self.scale_changed.emit(value)

    def _connect_func(self, ind: int):
        def beam_center_changed(value):
            self.beam_center[ind] = value
            self.change_center.emit(self.beam_center)

        def angle_zero_changed(value):
            self.zero_angle = value
            self.change_zero_angle.emit(self.zero_angle)

        def angle_direction_changed(value):
            self.angle_direction = value
            self.change_invert_angle.emit(self.angle_direction)

        if ind < 2:
            return beam_center_changed
        elif ind == 2:
            return angle_zero_changed
        else:
            return angle_direction_changed


class Basic2DImageWidget(AppNode, QMainWindow):

    def __init__(self, signal_connector, parent=None):
        AppNode.__init__(self, signal_connector)
        QMainWindow.__init__(self, parent)
        self.image_viewer = GiwaxsImageViewer(self.get_lower_connector(), self)
        self.setCentralWidget(self.image_viewer)
        self.__init_toolbar__()

    def __init_toolbar__(self):
        toolbar = self.addToolBar('Main')
        toolbar.setStyleSheet('background-color: black;')

        rotate_action = toolbar.addAction(Icon('rotate'), 'Rotate')
        rotate_action.triggered.connect(
            lambda: self.add_transformation('rotate_right'))

        flip_h = toolbar.addAction(Icon('flip_horizontal'), 'Horizontal flip')
        flip_h.triggered.connect(
            lambda: self.add_transformation('horizontal'))

        flip_v = toolbar.addAction(Icon('flip_vertical'), 'Vertical flip')
        flip_v.triggered.connect(
            lambda: self.add_transformation('vertical'))

        geometry_toolbar = self.addToolBar('Geometry')
        geometry_toolbar.setStyleSheet('background-color: black;')

        set_beam_center_action = toolbar.addAction(
            Icon('center'), 'Beam center')
        set_beam_center_action.triggered.connect(
            self.centralWidget().open_geometry_parameters)
