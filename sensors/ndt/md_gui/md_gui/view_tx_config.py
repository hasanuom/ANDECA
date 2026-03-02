from PyQt5.QtWidgets import *
import os
from callback_list import CallbackList
import sys
from enum import Enum, auto
import transmit_config
import transmit_tableview


class ViewTxConfig(CallbackList):
    class ButtonId(Enum):
        TX_SET = auto()
        TX_SAVE = auto()
        TX_READ = auto()
        TX_GET = auto()

    def __init__(self, tab_widget=None, tx_config=None):
        super().__init__()
        this_tab = QWidget()
        tab_layout = QHBoxLayout()
        this_tab.setLayout(tab_layout)
        tab_widget.addTab(this_tab, "TX Control")
        self._base_layout = tab_layout

        self._tx_config = tx_config
        self._max_but_height = 30
        self._max_but_width = 160

        self.tx_tableview = transmit_tableview.TransmitTableView(
                                                self._tx_config.harmonics,
                                                self._tx_config.max_number_frequencies)
        self._read_file_selection = self.file_selection("./tx_config")
        self._save_file_selection = self.file_selection("./tx_config")

        self._scale_sbox = QDoubleSpinBox()
        self._read_file_dir = self._read_file_selection.toPlainText()
        self._save_file_dir = self._save_file_selection.toPlainText()
        self.create_layout()

    def file_selection(self, default_path: str):
        file_selection = QTextEdit()
        file_selection.setText(default_path)
        file_selection.setMaximumSize(500, 25)
        #file_selection.setFixedHeight(20)
        file_selection.setFontPointSize(10)
        return file_selection

    def create_layout(self):
        layout = QHBoxLayout()
        layout.addWidget(self.create_transmit_box())
        self._base_layout.addLayout(layout)

    def file_open_picker(self):
        fname = QFileDialog().getOpenFileName(caption='Open file', directory=self._read_file_dir, filter="JSON (*json)")
        self._file_dir = os.path.dirname(os.path.abspath(fname[0]))
        self._read_file_selection.setText(fname[0])

    def file_save_picker(self):
        fname = QFileDialog().getSaveFileName(caption='Save file', directory=self._save_file_dir, filter="JSON (*json)")
        self._file_dir = os.path.dirname(os.path.abspath(fname[0]))
        self._save_file_selection.setText(fname[0])

    def on_any_changed(self):
        scale = self._scale_sbox.value()
        # dumb callback
        self.call_callback(self.ButtonId.TX_SET)

    def on_save(self):
        file = self._save_file_selection.toPlainText()
        #print(file)
        self.call_callback(self.ButtonId.TX_SAVE, (file,))

    def on_read(self):
        file = self._read_file_selection.toPlainText()
        #print(file)
        self.call_callback(self.ButtonId.TX_READ, (file,))

    def update(self):
        ''' Up date all parameters'''
        self.call_callback(self.ButtonId.TX_GET)

    @property
    def scale(self):
        return self._scale_sbox.value()

    @scale.setter
    def scale(self, val):
        self._scale_sbox.blockSignals(True)
        self._scale_sbox.setValue(val)
        self._scale_sbox.blockSignals(False)

    def _file_groupbox(self):
        _f_gbox = QGroupBox('File Selection')
        _f_gbox.setMaximumSize(100000, 100)
        _hbox = QGridLayout()

        _read_browse_btn = QPushButton("Browse")
        _read_browse_btn.setMaximumSize(self._max_but_width, self._max_but_height)
        _read_browse_btn.clicked.connect(self.file_open_picker)

        _save_browse_btn = QPushButton("Browse")
        _save_browse_btn.setMaximumSize(self._max_but_width, self._max_but_height)
        _save_browse_btn.clicked.connect(self.file_save_picker)

        _read_btn = QPushButton("Read")
        _read_btn.setMaximumSize(self._max_but_width, self._max_but_height)
        _read_btn.clicked.connect(self.on_read)

        _save_btn = QPushButton("Save")
        _save_btn.setMaximumSize(self._max_but_width, self._max_but_height)
        _save_btn.clicked.connect(self.on_save)

        _hbox.addWidget(_read_btn, 0, 0)
        _hbox.addWidget(self._read_file_selection, 0, 1, 1, 4)
        _hbox.addWidget(_read_browse_btn, 0, 5)

        _hbox.addWidget(_save_btn, 1, 0)
        _hbox.addWidget(self._save_file_selection, 1, 1, 1, 4)
        _hbox.addWidget(_save_browse_btn, 1, 5)

        _f_gbox.setLayout(_hbox)
        return _f_gbox


    def create_transmit_box(self):
        _get_btn = QPushButton("Get")
        _get_btn.clicked.connect(self.update)
        _get_btn.setMaximumSize(self._max_but_width, self._max_but_height)

        _set_btn = QPushButton("Set")
        _set_btn.clicked.connect(self.on_any_changed)
        _set_btn.setMaximumSize(self._max_but_width, self._max_but_height)

        _scale_label = QLabel("Scale(0-1)")
        self._scale_sbox = QDoubleSpinBox()
        self._scale_sbox.setDecimals(3)
        self._scale_sbox.setMaximum(1.0)
        self._scale_sbox.setMinimum(0.0)
        self._scale_sbox.setSingleStep(0.1)
        self._scale_sbox.setValue(0.85)
        self._scale_sbox.setMaximumSize(80, self._max_but_height)
        self._scale_sbox.valueChanged.connect(self.on_any_changed)

        _f_gbox = self._file_groupbox()

        layout = QFormLayout()
        layout.addRow(self.tx_tableview.tableview_widget)
        layout.addRow(_scale_label, self._scale_sbox)
        layout.addRow(_get_btn, _set_btn)
        layout.addRow(_f_gbox)

        tx_groupbox = QGroupBox("Tx Configuration")
        tx_groupbox.setLayout(layout)
        return tx_groupbox


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


    def file_event(self, file: tuple):
        # if isinstance(file, tuple):
        file = file[0] # unpack tuple
        print("file event\n\t" + file)


if __name__ == '__main__':

    events = Events()
    app = QApplication(sys.argv)
    main = QMainWindow()
    tx_config = transmit_config.TransmitConfig(events.button_event)

    tab_widget = QTabWidget()
    ct = ViewTxConfig(tab_widget, tx_config=tx_config)
    main.setCentralWidget(tab_widget)

    events = Events()

    ct.register_callback(ViewTxConfig.ButtonId.TX_SET, events.spinbox_event)
    ct.register_callback(ViewTxConfig.ButtonId.TX_SAVE, events.file_event)
    ct.register_callback(ViewTxConfig.ButtonId.TX_READ, events.file_event)
    ct.register_callback(ViewTxConfig.ButtonId.TX_GET, events.button_event)


    main.show()
    # main.show_maximized()
    print("TX Control Tab starting...")
    sys.exit(app.exec_())

