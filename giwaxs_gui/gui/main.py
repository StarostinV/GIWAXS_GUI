from PyQt5.QtWidgets import QMainWindow

from .dock_area import AppDockArea
from ..utils import center_widget, Icon


class GiwaxsProgram(QMainWindow):
    _MinimumSize = (500, 500)
    _InitSize = (1000, 700)

    def __init__(self):
        super(GiwaxsProgram, self).__init__()
        self.filepath = None
        self.__init_toolbar__()
        self.main_widget = AppDockArea()

        self.setCentralWidget(self.main_widget)
        self.setWindowTitle('GIWAXS analysis')
        self.setWindowIcon(Icon('window_icon'))
        self.setGeometry(0, 0, *self._InitSize)
        self.setMinimumSize(*self._MinimumSize)

        center_widget(self)
        self.show()

    def __init_toolbar__(self):
        # self.toolbar = self.addToolBar('File manager')
        #
        # open_image_action = QAction(Icon('add'), 'Open image', self)
        # open_image_action.setShortcut('Ctrl+A')
        # open_image_action.triggered.connect(self._open_image_dialog)
        # self.toolbar.addAction(open_image_action)

        docks_toolbar = self.addToolBar('Docks')

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


