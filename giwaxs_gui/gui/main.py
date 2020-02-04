from PyQt5.QtWidgets import QMainWindow, QWidget, QSizePolicy
from PyQt5.QtCore import Qt

from .dock_area import AppDockArea
from .basic_widgets import ToolBar
from ..utils import Icon


class GiwaxsProgram(QMainWindow):
    _MinimumSize = (500, 500)

    def __init__(self):
        super(GiwaxsProgram, self).__init__()
        self.filepath = None
        self.__init_toolbar__()
        self.main_widget = AppDockArea()

        self.setCentralWidget(self.main_widget)
        self.setWindowTitle('GIWAXS analysis')
        self.setWindowIcon(Icon('window_icon'))
        self.setMinimumSize(*self._MinimumSize)
        self.setWindowState(Qt.WindowMaximized)
        self.show()

        # center_widget(self)

    def __init_toolbar__(self):
        # self.toolbar = self.addToolBar('File manager')
        #
        # open_image_action = QAction(Icon('add'), 'Open image', self)
        # open_image_action.setShortcut('Ctrl+A')
        # open_image_action.triggered.connect(self._open_image_dialog)
        # self.toolbar.addAction(open_image_action)
        docks_toolbar = ToolBar('Docks', self)
        self.addToolBar(docks_toolbar)

        control_widget = docks_toolbar.addAction(Icon('folder'), 'File widget')
        control_widget.triggered.connect(lambda: self.main_widget.show_hide_docks('file_widget'))

        control_widget = docks_toolbar.addAction(Icon('control_widget'), 'Control widget')
        control_widget.triggered.connect(lambda: self.main_widget.show_hide_docks('control'))

        radial_profile = docks_toolbar.addAction(Icon('radial_profile'), 'Radial profile')
        radial_profile.triggered.connect(lambda: self.main_widget.show_hide_docks('radial_profile'))

        angular_profile = docks_toolbar.addAction(Icon('angular_profile'), 'Angular profile')
        angular_profile.triggered.connect(lambda: self.main_widget.show_hide_docks('angular_profile'))

        interpolation = docks_toolbar.addAction(Icon('interpolate'), 'Polar interpolation')
        interpolation.triggered.connect(lambda: self.main_widget.show_hide_docks('interpolation'))

        self.gen_toolbar = ToolBar('General')
        self.addToolBar(self.gen_toolbar)
        spacer_widget = QWidget()
        spacer_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer_widget.setVisible(True)
        self.gen_toolbar.addWidget(spacer_widget)

        self.fullscreen_action = self.gen_toolbar.addAction(Icon('tofullscreen'), 'Full screen')
        self.fullscreen_action.triggered.connect(self._on_fullscreen_changed)

    def _on_fullscreen_changed(self):
        if self.isFullScreen():
            self.setWindowState(Qt.WindowMaximized)
            self.fullscreen_action.setIcon(Icon('tofullscreen'))
        else:
            self.setWindowState(Qt.WindowFullScreen)
            self.fullscreen_action.setIcon(Icon('fromfullscreen'))

