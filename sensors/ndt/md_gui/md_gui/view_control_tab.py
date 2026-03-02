from PyQt5.QtWidgets import *

import sys
from enum import Enum, auto
from callback_list import CallbackList
import PyQt5.QtGui as QtGui


class ViewControlTab(CallbackList):
    class ButtonId(Enum):
        LOOP_ALPHA = auto()
        LOOP_CAL = auto()
        LOOP_RESET = auto()
        LOOP_CAL_VALS = auto()
        FCAL_SOURCE = auto()
        FCAL_CAL = auto()
        FCAL_VALS = auto()
        INFO_UPDATE = auto()
        INFO_VERSION = auto()
        # INFO_CLEAR_ERROR = auto()
        OP_RATE = auto()

    def __init__(self, tab_widget=None):
        super().__init__()
        this_tab = QWidget()
        tab_layout = QHBoxLayout()
        this_tab.setLayout(tab_layout)
        tab_widget.addTab(this_tab, "Control")
        self._base_layout = tab_layout

        self._max_but_width = 180
        self._max_but_height = 30

        self._file_dir = '.'

        # Initialise all call arguments to None
        self._call_args = dict()
        for item in self.ButtonId:
            self._call_args[item.name] = None
            # print(item.name)

        self.ui_console = QTextEdit()
        font = QtGui.QFont('Courier', 10)
        self.ui_console.setFont(font)
        self.create_layout()

    def create_layout(self):

        layout = QVBoxLayout()
        layout.addWidget(self.create_info_groupbox())
        layout.addWidget(self.create_loop_groupbox())
        layout.addWidget(self.create_fcal_groupbox())
        layout.addWidget(self.create_op_rate_groupbox())

        _hlayout = QHBoxLayout()
        _hlayout.addLayout(layout)
        _hlayout.addWidget(self.ui_console)

        self._base_layout.addLayout(_hlayout)

    @property
    def decimation_rate(self):
        return self._decimation_rate.value()

    @decimation_rate.setter
    def decimation_rate(self, val):
        self._decimation_rate.blockSignals(True)
        self._decimation_rate.setValue(val)
        self._decimation_rate.blockSignals(False)

    @property
    def op_dec_and_acc(self):
        return self._op_butgroup.checkedId()

    @op_dec_and_acc.setter
    def op_dec_and_acc(self, is_accumulate):
        self._op_butgroup.blockSignals(True)
        but = self._op_butgroup.button(1)
        # print(is_dec_and_acc)
        but.setChecked(is_accumulate)

        but = self._op_butgroup.button(0)
        but.setChecked(not is_accumulate)
        self._op_butgroup.blockSignals(False)

    # callback
    def on_op_rate_changed(self):
        op_rate_val = self._decimation_rate.value()
        # print(op_rate_val)
        but_id = self._op_butgroup.checkedId()
        # print(but_id)
        #
        #self.call_callback(self.ButtonId.OP_RATE, (op_rate_val, but_id))
        # Just do a dumb callback - this is what callback function expects
        self.call_callback(self.ButtonId.OP_RATE)

    def create_op_rate_groupbox(self):
        self._op_butgroup = QButtonGroup()
        dec_but = QRadioButton("Decimate")
        dec_but.setToolTip("Decimate and through away samples")
        acc_dec_but = QRadioButton("Accumulate and Decimate")
        acc_dec_but.setToolTip("Decimate and accumulate (recommended)")
        # The second argument is the ID
        self._op_butgroup.addButton(dec_but, 0)
        self._op_butgroup.addButton(acc_dec_but, 1)
        # initial state
        dec_but.setChecked(False)
        acc_dec_but.setChecked(True)
        # connect
        self._op_butgroup.buttonClicked.connect(self.on_op_rate_changed)

        _label = QLabel("Decimation Rate")
        self._decimation_rate = QSpinBox()
        self._decimation_rate.setMaximum(100)
        self._decimation_rate.setMinimum(1)
        self._decimation_rate.setSingleStep(1)
        self._decimation_rate.setValue(2)
        self._decimation_rate.setMaximumSize(100, self._max_but_height)
        self._decimation_rate.valueChanged.connect(self.on_op_rate_changed)

        layout = QFormLayout()
        layout.addRow(dec_but)
        layout.addRow(acc_dec_but)
        layout.addRow(_label, self._decimation_rate)

        rate_groupbox = QGroupBox("Output Data Rate")
        rate_groupbox.setLayout(layout)
        return rate_groupbox

    @property
    def loop_sbox(self):
        return self._loop_sbox.value()

    @loop_sbox.setter
    def loop_sbox(self, val):
        self._loop_sbox.blockSignals(True)
        self._loop_sbox.setValue(val)
        self._loop_sbox.blockSignals(False)

    def on_loop_sbox_changed(self):
        value = self._loop_sbox.value()
        # this would probably better if supported by callback function
        # self.call_callback(self.ButtonId.LOOP_ALPHA, (value,))
        # dumb callback
        self.call_callback(self.ButtonId.LOOP_ALPHA)

    def create_loop_groupbox(self):
        """compensation loop"""
        _loop_sbox_label = QLabel("Alpha (0 - 1)")
        self._loop_sbox = QDoubleSpinBox()
        self._loop_sbox.setToolTip("Loop feedback alpha value - suggest < 0.5")
        self._loop_sbox.setDecimals(4)
        self._loop_sbox.setMaximum(100.0) # TODO: max should really be 1.0
        self._loop_sbox.setMinimum(0.0)
        self._loop_sbox.setSingleStep(0.1)
        self._loop_sbox.setValue(0.5)
        self._loop_sbox.setMaximumSize(120, 30)
        # this works but moved to on_changed for external update funcitonality
        #self._loop_sbox.valueChanged.connect(lambda value,
        #                                            func=self.call_callback: func(ControlTabButtonId.LOOP_ALPHA, value))
        self._loop_sbox.valueChanged.connect(self.on_loop_sbox_changed)

        self._loop_cal_btn = QPushButton("Calibrate")
        self._loop_cal_btn.setToolTip("Perform Loop Calibration")
        self._loop_cal_btn.setMaximumSize(self._max_but_width, self._max_but_height)

        self._loop_reset_btn = QPushButton("Calibration Reset")
        self._loop_reset_btn.setToolTip("Reset Loop Calibration")
        self._loop_reset_btn.setMaximumSize(self._max_but_width, self._max_but_height)

        self._loop_val_btn = QPushButton("Calibration Values")
        self._loop_val_btn.setToolTip("Get Loop Calibration Values")
        self._loop_val_btn.setMaximumSize(self._max_but_width, self._max_but_height)

        self._loop_cal_btn.clicked.connect(lambda x: self.call_callback(self.ButtonId.LOOP_CAL))
        self._loop_reset_btn.clicked.connect(lambda x: self.call_callback(self.ButtonId.LOOP_RESET))
        self._loop_val_btn.clicked.connect(lambda x: self.call_callback(self.ButtonId.LOOP_CAL_VALS))

        layout = QFormLayout()
        layout.addRow(_loop_sbox_label, self._loop_sbox)
        layout.addRow(self._loop_cal_btn)
        layout.addRow(self._loop_val_btn)
        layout.addRow(self._loop_reset_btn)

        loop_groupbox = QGroupBox("Loop")
        loop_groupbox.setLayout(layout)
        return loop_groupbox

    @property
    def fcal_source_is_trans(self):
        return not self._ss_butgroup.checkedId()

    @fcal_source_is_trans.setter
    def fcal_source_is_trans(self, is_trans: bool) -> None:
        self._ss_butgroup.blockSignals(True)
        but = self._ss_butgroup.button(0)
        print(is_trans)
        but.setChecked(not is_trans)

        but = self._ss_butgroup.button(1)
        but.setChecked(is_trans)
        self._ss_butgroup.blockSignals(False)

    def on_fcal_source_changed(self):
        but_id = self._ss_butgroup.checkedId()
        print(but_id)
        #self.call_callback(self.ButtonId.FCAL_SOURCE, (but_id,))
        # dumb callback
        self.call_callback(self.ButtonId.FCAL_SOURCE)

    def create_fcal_groupbox(self):
        main_gbox = QGroupBox("Ferrite calibration")
        main_layout = QVBoxLayout()

        source_gbox = QGroupBox("Source Select")
        self._ss_butgroup = QButtonGroup(source_gbox)
        rx_sel = QRadioButton("RX")
        rx_sel.setToolTip("Use RX values as a source for ferrite calibration")

        trans_sel = QRadioButton("Transimpedance")
        trans_sel.setToolTip("Use Transimpedance values as a source for ferrite calibration")
        # The second argument is the ID
        self._ss_butgroup.addButton(rx_sel, 0)
        self._ss_butgroup.addButton(trans_sel, 1)

        # initial state
        rx_sel.setChecked(False)
        trans_sel.setChecked(True)
        # connect
        # Because buttonClicked returns a button object we need to use an 'on_changed' function to get the id
        # self._ss_butgroup.buttonClicked.connect(lambda value, func=self.call_callback: func(TabControlButtonId.FCAL_SOURCE, value))
        self._ss_butgroup.buttonClicked.connect(self.on_fcal_source_changed)

        source_layout = QVBoxLayout()
        source_layout.addWidget(rx_sel)
        source_layout.addWidget(trans_sel)
        source_gbox.setLayout(source_layout)

        fcal_gbox = QGroupBox("Calibration")
        fcal_layout = QVBoxLayout()
        _cal_btn = QPushButton("Calibrate")
        _cal_btn.setToolTip("Ferrite Calibration")
        _cal_btn.setMaximumSize(self._max_but_width, self._max_but_height)

        _val_btn = QPushButton("Calibration Values")
        _val_btn.setToolTip("Get Calibration Values")
        _val_btn.setMaximumSize(self._max_but_width, self._max_but_height)

        _cal_btn.clicked.connect(lambda x: self.call_callback(self.ButtonId.FCAL_CAL))
        _val_btn.clicked.connect(lambda x: self.call_callback(self.ButtonId.FCAL_VALS))

        fcal_layout.addWidget(_cal_btn)
        fcal_layout.addWidget(_val_btn)
        fcal_gbox.setLayout(fcal_layout)

        main_layout.addWidget(source_gbox)
        main_layout.addWidget(fcal_gbox)
        main_gbox.setLayout(main_layout)
        return main_gbox

    def create_info_groupbox(self):
        _version_btn = QPushButton("Version")
        _version_btn.setToolTip("Firmware Version Information")
        _version_btn.setMaximumSize(self._max_but_width, self._max_but_height)

        _update_status_btn = QPushButton("Update GUI")
        _update_status_btn.setToolTip("Update GUI - sync with board")
        _update_status_btn.setMaximumSize(self._max_but_width, self._max_but_height)

        # _clear_error_btn = QPushButton("Clear Error")
        # _clear_error_btn.setToolTip("Clear BIST errors")
        # _clear_error_btn.setMaximumSize(self._max_but_width, self._max_but_height)

        # Set Action
        _version_btn.clicked.connect(lambda x: self.call_callback(self.ButtonId.INFO_VERSION))
        _update_status_btn.clicked.connect(lambda x: self.call_callback(self.ButtonId.INFO_UPDATE))
        #_clear_error_btn.clicked.connect(lambda x: self.call_callback(self.ButtonId.INFO_CLEAR_ERROR))

        layout = QFormLayout()
        layout.addRow(_version_btn)
        layout.addRow(_update_status_btn)
        #layout.addRow(_clear_error_btn)

        info_groupbox = QGroupBox("Information")
        info_groupbox.setLayout(layout)
        return info_groupbox

    def update(self):
        ''' Update method - may help with sync'ing up the system
            Useful if the setters have been called directly e.g. at startup

            Call everything with memory. i.e. radiobuttons / spin boxes
            AND also have a state in the firmware
        '''
        self.on_op_rate_changed()
        self.on_fcal_source_changed()
        self.on_loop_sbox_changed()




# --------------------------------------------------------------------
# Everything below this line is for testing
# --------------------------------------------------------------------
class Events:

    def __init__(self):
        self._num = 0

    #@staticmethod
    def tbox_event(self, d : dict):
        print("tbox event " + str(d))

    #@staticmethod
    def spinbox_event(self, number):
        print("spinbox event " + str(number))

    #@staticmethod
    def radio_button_event(self, number):
        print("radio button event " + str(number))

    #@staticmethod
    def multiple_event(self, val, *vals):
        txt = "multiple vals\n val{0}".format(val)
        # txt = "multiple vals\n val{0}\n*vals{1}".format(val, *vals)
        # txt="dfsf"
        print(txt)

    #@staticmethod
    def button_event(self):
        print("button event")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = QMainWindow()

    tab_widget = QTabWidget()
    tab1 = QWidget()
    tab1_layout = QHBoxLayout()
    tab1.setLayout(tab1_layout)

    #ct = ViewControlTab(tab1_layout)
    ct = ViewControlTab(tab_widget)
    #tab_widget.addTab(tab1, "Control Test")
    main.setCentralWidget(tab_widget)

    events = Events()

    # register some events
    ct.register_callback(ct.ButtonId.LOOP_CAL, events.button_event)
    ct.register_callback(ct.ButtonId.LOOP_RESET, events.button_event)
    ct.register_callback(ct.ButtonId.LOOP_CAL_VALS, events.button_event)
    ct.register_callback(ct.ButtonId.LOOP_ALPHA, events.spinbox_event)
    ct.register_callback(ct.ButtonId.OP_RATE, events.multiple_event)

    ct.register_callback(ct.ButtonId.INFO_VERSION, events.button_event)
    ct.register_callback(ct.ButtonId.INFO_UPDATE, events.button_event)
    ct.register_callback(ct.ButtonId.INFO_CLEAR_ERROR, events.button_event)
    #
    ct.register_callback(ct.ButtonId.FCAL_CAL, events.button_event)
    ct.register_callback(ct.ButtonId.FCAL_VALS, events.button_event)
    ct.register_callback(ct.ButtonId.FCAL_SOURCE, events.radio_button_event)

    # Set some things
    ct.loop_sbox = 0.024
    ct.decimation_rate = 7
    ct.op_dec_and_acc = False
    ct.ui_console.setText("Hello World")
    ct.fcal_source_is_trans = True


    print(ct.decimation_rate)
    print(ct.op_dec_and_acc)
    print(ct.fcal_source_is_trans)
    print(ct.loop_sbox)


    ct.update()

    ct.loop_sbox  =0.99

    main.show()
    # main.show_maximized()
    print("Control Tab starting...")
    sys.exit(app.exec_())
