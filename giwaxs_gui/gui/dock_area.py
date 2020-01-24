import logging
from collections import defaultdict

from pyqtgraph.dockarea import DockArea, Dock

from .signal_connection import AppDataHolder, AppNode, SignalContainer
from .control_widget import ControlWidget
from .plot_widgets import Basic2DImageWidget
from .interpolation_widget import InterpolateImageWidget
from .radial_profile_widget import RadialProfileWidget
from .angular_profile_widget import AngularProfileWidget
from .file_widget import FileWidget

logger = logging.getLogger(__name__)


class AppDockArea(DockArea, AppNode):
    def __init__(self):
        DockArea.__init__(self)
        AppNode.__init__(self, AppDataHolder())
        self._status_dict = defaultdict(lambda: True)

        self.__init_image_view__()
        self.__init_control_widget__()
        self.__init_interpolate_widget__()
        self.__init_radial_widget__()
        self.__init_file_widget__()
        self.__init_angular_widget__()

        self._DOCK_DICT = {'interpolation': self.interpolation_dock,
                           'radial_profile': self.radial_profile_dock,
                           'control': self.control_dock,
                           'image_view': self.image_view_dock,
                           'file_widget': self.file_dock,
                           'angular_profile': self.angular_profile_dock}
        self.__apply_default_view__()

    def __apply_default_view__(self):
        self.show_hide_docks('interpolation')
        self.show_hide_docks('radial_profile')
        self.show_hide_docks('angular_profile')
        self.show_hide_docks('control')

    def __init_image_view__(self):
        self.image_view = Basic2DImageWidget(
            self.get_lower_connector('Basic2DImageWidget'))
        dock = Dock('Image')
        dock.addWidget(self.image_view)
        self.addDock(dock, size=(1000, 1000))
        self.image_view_dock = dock

    def __init_interpolate_widget__(self):
        self.interpolate_view = InterpolateImageWidget(
            self.get_lower_connector('InterpolateImageWidget'), self)
        dock = Dock('Interpolate')
        dock.addWidget(self.interpolate_view)
        self.addDock(dock, position='right')
        self.interpolate_view.update_image()
        self.interpolation_dock = dock

    def __init_radial_widget__(self):
        self.radial_profile = RadialProfileWidget(
            self.get_lower_connector('RadialProfileWidget'), self)
        dock = Dock('Radial Profile')
        dock.addWidget(self.radial_profile)
        self.addDock(dock, position='bottom')
        self.radial_profile.update_image()
        self.radial_profile_dock = dock

    def __init_angular_widget__(self):
        self.angular_profile = AngularProfileWidget(
            self.get_lower_connector('AngularProfileWidget'), self)
        dock = Dock('Angular Profile')
        dock.addWidget(self.angular_profile)
        self.addDock(dock, position='bottom')
        self.angular_profile.update_image()
        self.angular_profile_dock = dock

    def __init_control_widget__(self):
        self.control_widget = ControlWidget(
            self.get_lower_connector('ControlWidget'), self)
        control_dock = Dock('Segments')
        control_dock.addWidget(self.control_widget)
        self.addDock(control_dock, position='right')
        self.control_dock = control_dock

    def __init_file_widget__(self):
        self.file_widget = FileWidget(self.get_lower_connector('FileWidget'), self)
        self.file_dock = Dock('Files')
        self.file_dock.addWidget(self.file_widget)
        self.addDock(self.file_dock, position='left')

    def update_plot(self, image):
        SignalContainer(app_node=self).data_changed(image).send()

    def show_hide_docks(self, dock_name: str):
        assert dock_name in self._DOCK_DICT.keys()
        dock = self._DOCK_DICT[dock_name]
        status = self._status_dict[dock_name]
        if status:
            dock.hide()
        else:
            dock.show()
        self._status_dict[dock_name] = not status

