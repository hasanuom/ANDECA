import unittest

import main_gui_window
from PyQt5.QtWidgets import *
from pyqtgraph.Qt import QtCore, QtGui
import sys
from enum import Enum,auto
from md_command_const import NullState, StreamingState

import view_sidebar

class MyTest:
    def __init__(self):
        pass

    def tx_something(self, value : tuple):
        print('TX Enabled: ' + str(value))

    def fcal_something(self, value : tuple):
        print('Fcal_en Enabled: ' + str(value))

    def fcal_cal_something(self, value: tuple):
        print('Fcal_cal : ' + str(value))

    def null_something(self, value : tuple):
        print('null value: ' + str(value))

    def record_something(self, value: tuple):
        print('record : ' + str(value))

    def mark_something(self, value: tuple):
        print('mark: ' + str(value))

    def streaming_something(self, adict : tuple):
        for item in adict[0].items():
            print(item)

    def test_register(self, sbar):
        sbar.register_callback(view_sidebar.SidebarCallbackId.TX_EN, self.tx_something)
        sbar.register_callback(view_sidebar.SidebarCallbackId.FCAL_EN, self.fcal_something)
        sbar.register_callback(view_sidebar.SidebarCallbackId.NULLING, self.null_something)
        sbar.register_callback(view_sidebar.SidebarCallbackId.STREAMING, self.streaming_something)
        sbar.register_callback(view_sidebar.SidebarCallbackId.FCAL_CAL, self.fcal_cal_something)
        sbar.register_callback(view_sidebar.SidebarCallbackId.RECORD, self.record_something)
        sbar.register_callback(view_sidebar.SidebarCallbackId.MARK, self.mark_something)




if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = main_gui_window.MainWindow()
    sbar = view_sidebar.ViewSidebar(main)



    main.show_maximized()


    mytest = MyTest()
    mytest.test_register(sbar)
    print("toothpaste")
    sys.exit(app.exec_())
