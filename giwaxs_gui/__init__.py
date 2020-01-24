from giwaxs_gui.gui import GiwaxsProgram

if __name__ == '__main__':
    import sys
    import logging
    from PyQt5.QtWidgets import QApplication

    logging.basicConfig(level=logging.DEBUG)
    app = QApplication(sys.argv)
    window = GiwaxsProgram()
    sys.exit(app.exec_())
