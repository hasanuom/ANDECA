

import sys
import unittest

import pytest
from PyQt5.QtWidgets import *
from pytestqt.plugin import QtBot
import numpy as np
import numpy.testing as nt
sys.path.append("C:/Users/h43191kb/gitlab/md_gui/md_gui")
from enum import Enum, auto
from view_control_tab import ViewControlTab, ControlTabButtonId

import md_data_handle

# @pytest.fixture
# def app(qtbot):
#     app = QApplication(sys.argv)
#     main = QMainWindow()



class test_gui():

    def test_set_loop_spinbox(self):
        ct.fb_sbox = 0.024

    def test_upper(self):
        self.assertEqual('foo'.upper(), 'FOO')

    def test_isupper(self):
        self.assertTrue('FOO'.isupper())
        self.assertFalse('Foo'.isupper())

    def test_split(self):
        s = 'hello world'
        self.assertEqual(s.split(), ['hello', 'world'])
        # check that s.split fails when the separator is not a string
        with self.assertRaises(TypeError):
            s.split(2)



class Events:

    def __init__(self):
        self._num = 0

    def tbox_event(self, d : dict):
        print("tbox event " + str(d))

    def spinbox_event(self, number):
        print("spinbox event " + str(number))

    def radio_button_event(self, number):
        print("radio button event " + str(number))

    def multiple_event(self, val, *vals):
        print("multiple vals" + str(val) + str(*vals))

    def button_event(self):
        print("button event")


if __name__ == '__main__':

    app = QApplication(sys.argv)
    main = QMainWindow()

    tab_widget = QTabWidget()
    tab1 = QWidget()
    tab1_layout = QHBoxLayout()
    ct = ViewControlTab(tab1_layout)
    tab1.setLayout(tab1_layout)
    tab_widget.addTab(tab1, "Control Test")
    main.setCentralWidget(tab_widget)

    events = Events()
    # sbar = (main)
    #
    # # register some events
    ct.register_callback(ControlTabButtonId.LOOP_CAL, events.button_event)
    ct.register_callback(ControlTabButtonId.LOOP_RESET, events.button_event)
    ct.register_callback(ControlTabButtonId.LOOP_CAL_VALS, events.button_event)
    ct.register_callback(ControlTabButtonId.LOOP_ALPHA, events.spinbox_event)
    ct.register_callback(ControlTabButtonId.OP_RATE, events.multiple_event)
    # sbar.register_callback(ButtonId.TX_EN, events.radio_button_event)
    # sbar.register_callback(ButtonId.NULLING, events.radio_button_event)
    # sbar.register_callback(ButtonId.FCAL_CAL, events.button_event)
    # sbar.register_callback(ButtonId.FCAL_EN, events.radio_button_event)
    # sbar.register_callback(ButtonId.RECORD, events.button_event)
    # sbar.register_callback(ButtonId.MARK, events.button_event)
    #
    # # Try setting something

    ct.fb_sbox = 0.024
    ct.decimation_rate = 7
    ct.op_dec_and_acc = False

    main.show()
    qtbot.addWidget(main)
    # main.show_maximized()
    print("Control Tab starting...")

    unittest.main()

    sys.exit(app.exec_())

