from PyQt5.QtWidgets import *
from PyQt5 import QtCore
from PyQt5 import QtGui
import sys


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Semis MD")

        # layout = QGridLayout()
        # layout.setColumnStretch(0, 4)
        # layout.setColumnStretch(1, 4)
        # label_commsport = QLabel("Central")
        # layout.addWidget(label_commsport, 1,1 )

        # Menu bar
        self._menubar = self.menuBar()
        self._init_menu()

        # Tab widget
        self._tab_widget = QTabWidget()
        self._init_tab_widget()

        # Dock widgets settings - set before adding any dockwidget
        x = self.dockOptions()
        # self.AnimatedDocks = False
        self.setDockOptions(self.dockOptions() & ~self.AnimatedDocks)
        # self.AllowNestedDocks = False
        self.setDockNestingEnabled(False)
        # self.AllowTabbedDocks = False
        self.setDockOptions(self.dockOptions() & ~self.AllowTabbedDocks)
        # self.ForceTabbedDocks = False
        self.setDockOptions(self.dockOptions() & ~self.ForceTabbedDocks)
        # self.VerticalTabs = True
        self.setDockOptions(self.dockOptions() & ~self.VerticalTabs)
        # self.GroupedDragging = False
        self.setDockOptions(self.dockOptions() & ~self.GroupedDragging)

        print(x)
        self._sidebar = MyDockWidget('Control')
        self.addDockWidget(QtCore.Qt.DockWidgetArea(0x1), self._sidebar)

        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("My status Bar message")
        self.setStatusBar(self.status_bar)

        # Manage main window
        self.setCentralWidget(self._tab_widget)
        self.setWindowIcon(QtGui.QIcon('../resources/UoM-icon.png'))
        # self.show()

    def _init_menu(self):
        self._menubar.addMenu('file')  # just an example

    def _init_tab_widget(self):
        self._tab_widget.setElideMode(QtCore.Qt.ElideRight)
        self._tab_widget.setTabsClosable(False)
        self._tab_widget.setMovable(True)
        self._tab_widget.setObjectName("tab_main")
        # Only add a tab for testing
        # self._tab_widget.addTab(QLabel('tab 1'), 'Tab 1')
        # self._tab_widget.setTabText(0, "adfasf")

    def get_sidebar_widget(self):
        return self._sidebar

    def get_tab_widget(self):
        return self._tab_widget

    def get_statusbar_widget(self):
        return self.status_bar

    def get_menubar_widget(self):
        return self._menubar

    def _sbar_test(self):
        sbar = self.get_statusbar_widget()
        sbar.showMessage("newMessage")

    def show_maximized(self):
        # overload
        self.showMaximized()  # Main window maximized
        self.show()


class MyDockWidget(QDockWidget):
    def __init__(self, *kargs):
        super().__init__()

    def closeEvent(self, QCloseEvent):
        # don't close
        print("close event overridden")
        pass


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())
