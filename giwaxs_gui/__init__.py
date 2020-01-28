import sys
import logging
from PyQt5.QtWidgets import QApplication

from .gui import GiwaxsProgram

__all__ = ['GiwaxsProgram', 'run']


def run():
    # TODO: add logging config
    logging.basicConfig(level=logging.ERROR)
    app = QApplication(sys.argv)
    window = GiwaxsProgram()
    sys.exit(app.exec_())
