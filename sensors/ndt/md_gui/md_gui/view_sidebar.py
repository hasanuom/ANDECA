import main_gui_window
from PyQt5.QtWidgets import *
import PyQt5.QtCore
import sys
from enum import Enum,auto
from md_const import NullState, StreamingState
from callback_list import CallbackList

class ViewSidebar(CallbackList):
    class ButtonId(Enum):
        TX_EN = auto()
        NULLING = auto()
        FCAL_CAL = auto()
        FCAL_EN = auto()
        RECORD = auto()
        MARK = auto()
        BIST_ERROR_CLEAR = auto()
        STREAMING = auto()
        AUDIO_STATE = auto()
        AUDIO_COMP = auto()
        THRESHOLD = auto()

    def __init__(self, sidebar):
        super().__init__()
        #self._sbar = mainwindow.get_sidebar_widget()
        self._sbar = sidebar
        # To make it so we can't close it we just set the other the other features
        sidebar.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

        self._widget = QWidget()

        layout = QVBoxLayout()
        layout.addWidget(self._stream_group())
        layout.addWidget(self._tx_en_group())
        layout.addWidget(self._nulling_group())
        layout.addWidget(self._ferrite_group())
        layout.addWidget(self._record_data_group())
        layout.addWidget(self._error_group())
        layout.addWidget(self._detection_group())

        self._widget.setLayout(layout)
        self._sbar.setWidget(self._widget)

        self._tx_en_text = {"on": "Tx Active", "off": "Tx Off"}
        self._detection_threshold = 0
        self._audio_comp = 0

    def _stream_group(self):
        groupbox = QGroupBox("Streaming")
        layout = QVBoxLayout()

        temp = []
        for item in StreamingState:
            temp.append((item.name, QCheckBox(item.name)))

        self._streaming_cbox = dict(temp)
        for key in self._streaming_cbox:
            layout.addWidget(self._streaming_cbox[key])
            self._streaming_cbox[key].clicked.connect(self._on_change_streaming)
        groupbox.setLayout(layout)
        return groupbox


    # Left as a radio button implementation
    # def _tx_control(self):
    #     groupbox = QGroupBox("TX Control")
    #     layout = QVBoxLayout()
    #     self._tx_control_radio = [QRadioButton("Enabled"), QRadioButton("Disabled")]
    #     for b in self._tx_control_radio:
    #         layout.addWidget(b)
    #
    #     self._tx_control_radio[0].setChecked(False)
    #     self._tx_control_radio[1].setChecked(True)
    #     self._tx_control_radio[0].toggled.connect(self._on_change_tx_enable)
    #
    #     groupbox.setLayout(layout)
    #     return groupbox

    def _tx_en_group(self):
        groupbox = QGroupBox("TX Enable")
        layout = QVBoxLayout()
        self._tx_en_but = QPushButton("Tx Off")
        self._tx_en_but.setCheckable(True)
        # self._tx_en_but.setChecked(False)
        self._tx_en_but.setChecked(True)
        self._tx_en_but.setStyleSheet(
            "QPushButton {background-color: none;\n}"
            "QPushButton::checked {background-color: orange;\n text: 'wibble';\n}"
        )

        self._tx_en_but.clicked.connect(self._on_change_tx_enable)
        layout.addWidget(self._tx_en_but)
        groupbox.setLayout(layout)
        return groupbox


    def _ferrite_group(self):

        self._fcal_but = QPushButton("Calibrate")
        self._fcal_but.setStyleSheet(
            "QPushButton {background-color: none;\n}"
            "QPushButton::pressed {background-color: red;\n}"
        )
        self._fcal_but.clicked.connect(lambda x: self.call_callback(self.ButtonId.FCAL_CAL))

        self._fcal_butgroup = QButtonGroup()
        self._fcal_radio = [QRadioButton("Enabled"), QRadioButton("Disabled")]
        for b in self._fcal_radio:
            self._fcal_butgroup.addButton(b)

        self._fcal_radio[0].setChecked(False)
        self._fcal_radio[1].setChecked(True)
        self._fcal_butgroup.buttonClicked.connect(self._on_changed_fcal_en)


        self._fcal_group = QGroupBox("Ferrite Calibration")
        layout = QVBoxLayout()
        layout.addWidget(self._fcal_but)
        for b in self._fcal_butgroup.buttons():
            layout.addWidget(b)
        self._fcal_group.setLayout(layout)
        return self._fcal_group

    def _nulling_group(self):

        self._null_butgroup = QButtonGroup()
        self._nulling_radio = [QRadioButton("Active"), QRadioButton("Paused"), QRadioButton("Zeroed")]
        for b in self._nulling_radio:
            self._null_butgroup.addButton(b)

        self._nulling_radio[0].setChecked(True)
        self._null_butgroup.buttonClicked.connect(self._on_change_null_state)

        self._null_group = QGroupBox("Nulling")
        layout = QVBoxLayout()
        for b in self._null_butgroup.buttons():
            layout.addWidget(b)
        self._null_group.setLayout(layout)
        return self._null_group

    def _error_group(self):

        self._error_label = QLabel()
        self._error_label.setText('No error')

        self._error_led = self._init_led_widget()

        self._clear_error_btn = QPushButton("Clear Error")
        self._clear_error_btn.setToolTip("Clear BIST errors")
        #_clear_error_btn.setMaximumSize(self._max_but_width, self._max_but_height)

        # Set Action
        self._clear_error_btn.clicked.connect(self._on_changed_bist_clear_error)

        layout = QFormLayout()

        layout.addRow(self._error_led)
        layout.addRow(self._error_label)
        layout.addRow(self._clear_error_btn)

        error_groupbox = QGroupBox("Error")
        error_groupbox.setLayout(layout)
        return error_groupbox

    def _detection_group(self):
        groupbox = QGroupBox('Detection')
        layout = QVBoxLayout()
        self._audio_active_checkbox = QCheckBox('Audio')

        threshold_label = QLabel('Threshold')
        self._detection_threshold_ctrl = QDoubleSpinBox()
        self._detection_threshold_ctrl.setMinimum(0)
        self._detection_threshold_ctrl.setMaximum(1000)
        self._detection_threshold_ctrl.setValue(1.5)
        self._detection_threshold_ctrl.setDecimals(3)
        self._detection_threshold_ctrl.setStepType(QAbstractSpinBox.AdaptiveDecimalStepType)


        self._audio_component_radio = [QRadioButton() for _ in range(2)]
        labels = ['Upper Plot', 'Lower Plot']
        for k, radio in enumerate(self._audio_component_radio):
            radio.setText(labels[k])
            radio.clicked.connect(self._on_change_audio_comp)

        self._audio_component_radio[0].setChecked(1)

        layout.addWidget(self._audio_active_checkbox)
        [layout.addWidget(radio) for radio in self._audio_component_radio]
        layout.addWidget(threshold_label)
        layout.addWidget(self._detection_threshold_ctrl)

        self._audio_active_checkbox.stateChanged.connect(self._on_change_audio_state)
        self._detection_threshold_ctrl.valueChanged.connect(self._on_change_detection_threshold)

        groupbox.setLayout(layout)
        return groupbox

    def _init_led_widget(self):
        led_widget = QPushButton()
        led_widget.setStyleSheet(
            "QPushButton {background-color: green;\n}"
            "QPushButton::checked {background-color: red;\n}"
        )
        led_widget.setAutoFillBackground(True)
        led_widget.setCheckable(True)
        led_widget.setDisabled(True)
        led_widget.blockSignals(True)
        return led_widget

    @property
    def bist_error(self):
        return self._error_led.isChecked()

    @bist_error.setter
    def bist_error(self, is_error):
        self._error_led.setChecked(is_error)

    def _on_changed_bist_clear_error(self):
        self.bist_error = False
        self._error_label.setText("No error")
        self.call_callback(self.ButtonId.BIST_ERROR_CLEAR)

    @property
    def audio_state(self):
        return self._audio_active_checkbox.isChecked()

    @audio_state.setter
    def audio_state(self, enable: bool):
        self._audio_active_checkbox.setChecked(enable)

    def _on_change_audio_state(self):
        self.call_callback(self.ButtonId.AUDIO_STATE, (self.audio_state,))

    @property
    def audio_comp(self):
        if self._audio_component_radio[0].isChecked():
            self._audio_comp = 0
        elif self._audio_component_radio[1].isChecked():
            self._audio_comp = 1
        return self._audio_comp

    @audio_comp.setter
    def audio_comp(self, comp):
        self._audio_comp = comp


    def _on_change_audio_comp(self):
        self.call_callback(self.ButtonId.AUDIO_COMP, (self.audio_comp,))

    @property
    def detection_threshold(self):
        return self._detection_threshold_ctrl.value()

    @detection_threshold.setter
    def detection_threshold(self, value):
        self._detection_threshold = value

    def _on_change_detection_threshold(self):
        self.call_callback(self.ButtonId.THRESHOLD, (self.detection_threshold,))


    @property
    def error_code(self):
        return self._error_code

    @error_code.setter
    def error_code(self, code):
        print("bist_error code {0}".format(code))
        self._error_label.setText(code)

    def _record_data_group(self):
        groupbox = QGroupBox("Record")
        layout = QVBoxLayout()
        self._recording_but = QPushButton("Start")
        self._recording_but.setStyleSheet(
            "QPushButton {background-color: none;\n}"
            "QPushButton::checked {background-color: orange;\n}"
        )
        self._recording_but.setCheckable(True)

        self._recording_but.clicked.connect(self._on_change_record)
        layout.addWidget(self._recording_but)

        self._mark_but = QPushButton("Mark")
        self._mark_but.setStyleSheet(
            "QPushButton {background-color: none;\n}"
            "QPushButton::pressed {background-color: red;\n}"
        )
        self._mark_but.clicked.connect(lambda x: self.call_callback(self.ButtonId.MARK))
        layout.addWidget(self._mark_but)
        groupbox.setLayout(layout)
        return groupbox

    #
    # Record
    #
    def _on_change_record(self):
        is_recording = self._recording_but.isChecked()
        if is_recording:
            # start recording data to a file
            self._recording_but.setText("Recording")
        else:
            # stop recording
            self._recording_but.setText("Start")

        self.call_callback(self.ButtonId.RECORD, (is_recording,))

    #
    # Streaming
    #
    @property
    def streaming_select(self):
        temp = dict()
        for item in StreamingState:
            temp[item.name]= self._streaming_cbox[item.name].isChecked()
        #print(temp)
        return temp

    @streaming_select.setter
    def streaming_select(self, ip: dict):
        for key in self._streaming_cbox:
            self._streaming_cbox[key].blockSignals(True)

        for key in ip:
            try:
               self._streaming_cbox[key].setChecked(ip[key])
            except KeyError:
               print("sidebar streaming key error")

        for key in self._streaming_cbox:
            self._streaming_cbox[key].blockSignals(False)

    def _on_change_streaming(self):
        temp = self.streaming_select
        self.call_callback(self.ButtonId.STREAMING.name, (temp,))

    #
    # TX enable
    #
    @property
    def tx_enable(self):
        return self._tx_en_but.isChecked()

    @tx_enable.setter
    def tx_enable(self, enable: bool):
        self._tx_en_but.blockSignals(True)
        self._tx_en_but.setChecked(enable)
        self._tx_enable_set_text()
        self._tx_en_but.blockSignals(False)

    def _tx_enable_set_text(self):
        if self._tx_en_but.isChecked():
            self._tx_en_but.setText(self._tx_en_text["on"])
        else:
            self._tx_en_but.setText(self._tx_en_text["off"])

    def _on_change_tx_enable(self):
        self._tx_enable_set_text()
        self.call_callback(self.ButtonId.TX_EN, (self.tx_enable,))

    #
    # Ferrite Cal enable
    #
    @property
    def fcal_enable(self):
        return self._fcal_radio[0].isChecked()

    @fcal_enable.setter
    def fcal_enable(self, enable: bool):
        self._fcal_butgroup.blockSignals(True)
        self._fcal_radio[0].setChecked(enable)
        self._fcal_butgroup.blockSignals(False)

    def _on_changed_fcal_en(self):
        self.call_callback(self.ButtonId.FCAL_EN, (self.fcal_enable,))


    #
    # Nulling
    #
    @property
    def null_state(self):
        state = None
        if self._nulling_radio[0].isChecked():
            state = NullState.ACTIVE.value
        elif self._nulling_radio[1].isChecked():
            state = NullState.PAUSED.value
        elif self._nulling_radio[2].isChecked():
            state = NullState.ZEROED.value
        else:
            ValueError("null state has invalid value")
        return state

    @null_state.setter
    def null_state(self, state: NullState):
        self._null_butgroup.blockSignals(True)
        self._null_state = state
        if state == NullState.ACTIVE.value:
            self._nulling_radio[0].setChecked(True)
        elif state == NullState.PAUSED.value:
            self._nulling_radio[1].setChecked(True)
        elif state == NullState.ZEROED.value:
            self._nulling_radio[2].setChecked(True)
        else:
            ValueError("null state has invalid value")

        self._null_butgroup.blockSignals(False)

    def _on_change_null_state(self):
        # Radio button has changed - perform a callback
        self.call_callback(self.ButtonId.NULLING.name, self.null_state)



    def update(self):
        ''' Update method - may help with sync'ing up the system
            Useful if the setters have been called directly e.g. at startup

            Call everything with memory. i.e. radiobuttons / spin boxes
            AND also have a state in the firmware
        '''
        self._on_change_null_state()
        self._on_change_streaming()
        self._on_change_tx_enable()
        self._on_changed_fcal_en()
        # The Record can only ever change from GUI input - Therefore it never needs to be updated?
        # self._on_change_record()


# --------------------------------------------------------------------
# Everything below this line is for testing
# --------------------------------------------------------------------

class Events:
    def __init__(self):
        self._num = 0

    def tbox_event(self, d : tuple):
        print("tbox event " + str(d[0]))

    def radio_button_event(self, number):
        print("radio button event " + str(number))

    def button_event(self):
        print("button event")

    def record_event(self, val: tuple):
        print("record event {0}".format(val[0]))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = main_gui_window.MainWindow()

    events = Events()
    sidebar = main_window.get_sidebar_widget()
    sbar = ViewSidebar(sidebar)

    # register some events
    sbar.register_callback(sbar.ButtonId.STREAMING, events.tbox_event)
    sbar.register_callback(sbar.ButtonId.TX_EN, events.radio_button_event)
    sbar.register_callback(sbar.ButtonId.NULLING, events.radio_button_event)
    sbar.register_callback(sbar.ButtonId.FCAL_CAL, events.button_event)
    sbar.register_callback(sbar.ButtonId.FCAL_EN, events.radio_button_event)
    sbar.register_callback(sbar.ButtonId.RECORD, events.record_event)
    sbar.register_callback(sbar.ButtonId.MARK, events.button_event)

    # Try setting something
    sbar.streaming_select= {'FCAL': True, 'TRANS': False, 'RXV': True, 'TXI': True}
    sbar.tx_enable = False
    sbar.null_state = 0
    sbar.fcal_enable = False
    sbar.bist_error = True
    sbar.error_code = "0x12312"

    # main.show_maximized()
    main_window.show()
    print("Sidebar test")
    sys.exit(app.exec_())
