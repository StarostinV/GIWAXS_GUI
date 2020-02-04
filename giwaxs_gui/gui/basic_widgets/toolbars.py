from PyQt5.QtWidgets import QToolBar


class ToolBar(QToolBar):
    def __init__(self, name: str, parent=None, color: str = None, *,
                 disable_hide: bool = True, movable: bool = False):
        super().__init__(name, parent)
        if color:
            self.setStyleSheet(f'background-color: {color};')
        if disable_hide:
            self.toggleViewAction().setEnabled(False)
        self.setMovable(movable)


class BlackToolBar(ToolBar):
    def __init__(self, name: str, parent=None, **kwargs):
        super().__init__(name, parent, 'black', **kwargs)
