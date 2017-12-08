import sys
import signal


# PyQt Imports
from PyQt5 import QtGui as QtG

from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QMenu,
    QSystemTrayIcon,
    QWidget,
)

import qt_utils
from hotstrings import Hotstrings


class SysTray(QSystemTrayIcon):

    def __init__(self, parent=None):
        QSystemTrayIcon.__init__(
            self,
            QtG.QIcon("icons/butler.png"),
            parent
        )

        menu = QMenu(parent)
        menu.addAction(
            # TODO: Suspend script, so that all hotkeys & hotstrings stop
            QAction("&Quit", self, triggered=on_exit)
        )
        self.setContextMenu(menu)

        self.setToolTip("Chotu")


def on_exit(*args):
    Hotstrings.cleanup()
    QApplication.instance().quit()
    sys.exit()


def run():

    # Ensure proper cleanup
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, on_exit)

    app = QApplication(sys.argv)
    qt_utils.SignalWakeupHandler(app)

    # An empty widget that acts as the parent
    widget = QWidget()

    trayIcon = SysTray(widget)
    trayIcon.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    run()
