import sys  # We need sys so that we can pass argv to QApplication
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np

import main_gui_window
import view_time_domain
import view_spectrum_fra
import view_tx_config
import view_spectrum
import view_vector
import view_frequency_plot
import view_scatter
import view_scrolling_plot
import view_control_tab
import view_sidebar
import view_pos_scatter
import view_ssa
import view_processed
import view_waterfall

import presenter

from md_serial import MdSerialTransmit as SerialTx

import hwinterface

import parse_packet
import transmit_config
import md_const
# import cam_const
import md_data_handle
import cam_data_handle
import time
import record_data

import queue
import struct

import dialog_help
import dialog_comms
from md_const import NullState, StreamingState
from hwinterface import HwInterfaceZMQ

from detection import Detection


class Main(QtWidgets.QMainWindow):
    def __init__(self, main_window):
        super().__init__()
        self._main_window = main_window
        np.set_printoptions(threshold=sys.maxsize)

        # Flag for testing the connection dialog success / fail
        self._failed = False

        # Setup Connection using a dialog
        self.hw_factory = hwinterface.HwInterfaceFactory()
        self.dialog_comms = dialog_comms.DialogComms(self.hw_factory.create_interface)
        retval = self.dialog_comms.exec_()
        # Note: retval returns either QDialog::rejected == 0; QDialog::accepted == 1
        if retval == 0:
            # print("User Cancelled")
            self._failed = True
            return

        self.hw_interface = self.dialog_comms.hw_interface
        self._md_log = record_data.RecordData(self.hw_interface.message_log)

        # Camera interface
        self.cam_zmq = HwInterfaceZMQ(host="10.1.1.1", dataport=5002, stateport=5202, context=None,
                                      header=bytearray(b'\xF0\x0D\xBA\x11'))

        # Detection control
        self.detection = Detection(print_signal=False)

        # Set plot background to white - before loading ui(!)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        self._sidebar = view_sidebar.ViewSidebar(main_window.get_sidebar_widget())
        self.mode_tab_widget = main_window.get_tab_widget()

        # Create a queue for received packets
        self.queue_rx = queue.Queue(maxsize=99)
        self.queue_pos = queue.Queue(maxsize=99)

        self.md_tx = SerialTx(self.hw_interface)
        self.presenter = presenter.Presenter(self.md_tx, self._md_log)

        self.color_lookup = self.presenter.get_colors(16)

        # self.actionAbout.triggered.connect(self.dialog_about)

        #
        # Tx Config
        #
        self.tx_config = transmit_config.TransmitConfig(
            self._update_tx_config_callback)

        num_scrolling_points = 300
        num_harmonics_max = self.tx_config.max_number_frequencies

        self.md_parse = parse_packet.ParsePacket(self.queue_rx, self.tx_config)
        self.pos_parse = parse_packet.ParsePacket(self.queue_pos, self.tx_config)

        # Sidebar
        self._sidebar.register_callback(self._sidebar.ButtonId.STREAMING, self.presenter.send_stream_config)
        self._sidebar.register_callback(self._sidebar.ButtonId.RECORD, self.presenter._record_event)
        self._sidebar.register_callback(self._sidebar.ButtonId.MARK, self.presenter._mark_event)
        self._sidebar.register_callback(self._sidebar.ButtonId.TX_EN, self.presenter.send_tx_en_config)
        self._sidebar.register_callback(self._sidebar.ButtonId.NULLING, self.presenter.send_nulling_config)
        self._sidebar.register_callback(self._sidebar.ButtonId.FCAL_CAL, self.presenter.send_ferrite_calibrate)
        self._sidebar.register_callback(self._sidebar.ButtonId.FCAL_EN, self.presenter.send_ferrite_cal_enable)
        self._sidebar.register_callback(self._sidebar.ButtonId.BIST_ERROR_CLEAR, self.presenter.send_clear_error)
        self._sidebar.register_callback(self._sidebar.ButtonId.AUDIO_STATE, self.detection.audio_active)
        self._sidebar.register_callback(self._sidebar.ButtonId.AUDIO_COMP, self.detection.set_audio_comp)
        self._sidebar.register_callback(self._sidebar.ButtonId.THRESHOLD, self.detection.update_threshold)

        #
        # TABS
        #
        self.view_control = view_control_tab.ViewControlTab(self.mode_tab_widget)
        self.view_tx_config = view_tx_config.ViewTxConfig(self.mode_tab_widget, tx_config=self.tx_config)
        self.view_scatter = view_scatter.ViewScatterPlot(self.mode_tab_widget, color_lookup=self.color_lookup)
        self.view_scrolling = view_scrolling_plot.ViewScrolling(self.mode_tab_widget, color_lookup=self.color_lookup)
        self.view_vector = view_vector.ViewVectorPlot(self.mode_tab_widget, color_lookup=self.color_lookup)
        self.view_freq = view_frequency_plot.ViewFreqPlot(self.mode_tab_widget)
        self.view_spectrum = view_spectrum.ViewSpectrum(self.mode_tab_widget, self.presenter.get_spectrum_rx_event,
                                                        self.presenter.get_spectrum_tx_event)
        self.view_fra = view_spectrum_fra.ViewSpectrumFRA(self.mode_tab_widget, self.presenter.send_fra_control)
        self.view_time = view_time_domain.ViewTD(self.mode_tab_widget,
                                                 self.presenter.get_td_tx_event, self.presenter.get_td_nulling_event,
                                                 self.presenter.get_td_rx_event, self.presenter.get_td_txi_event)

        self.view_pos_scatter = view_pos_scatter.ViewPosScatterPlot(self.mode_tab_widget,
                                                                    color_lookup=self.color_lookup)

        self.view_ssa = view_ssa.ViewSSALinePlot(self.mode_tab_widget)
        self.view_processed = view_processed.ViewProcessed(self.mode_tab_widget)
        self.view_waterfall = view_waterfall.ViewWaterfall(self.mode_tab_widget)

        #
        # Data Handler
        #
        self.dhandler = md_data_handle.DataHandler(self.tx_config)
        self.cam_data_handler = cam_data_handle.CamDataHandler()

        self.md_parse.register_callback(self.md_parse.ParseId.STREAM_FCAL, self.dhandler.update_data)
        self.md_parse.register_callback(self.md_parse.ParseId.STREAM_TRANS, self.dhandler.update_data)
        self.md_parse.register_callback(self.md_parse.ParseId.STREAM_RXV, self.dhandler.update_data)
        self.md_parse.register_callback(self.md_parse.ParseId.STREAM_TXI, self.dhandler.update_data)
        self.md_parse.register_callback(self.md_parse.ParseId.FW_VERSION, self.update_console_text)
        self.md_parse.register_callback(self.md_parse.ParseId.LOOP_CAL_VALS, self.update_console_text)
        self.md_parse.register_callback(self.md_parse.ParseId.TIME_DOMAIN, self.view_time.update)
        self.md_parse.register_callback(self.md_parse.ParseId.SPECTRUM, self.view_spectrum.update)
        self.md_parse.register_callback(self.md_parse.ParseId.SETTINGS, self.update_settings)
        self.md_parse.register_callback(self.md_parse.ParseId.STREAM_SETTINGS, self.update_streaming_settings)
        self.md_parse.register_callback(self.md_parse.ParseId.TX_ENABLE, self.update_tx_enable)
        self.md_parse.register_callback(self.md_parse.ParseId.LOOP_SETTINGS, self.update_nulling_status)
        self.md_parse.register_callback(self.md_parse.ParseId.FERRITE_CAL_VALS, self.update_console_text)
        self.md_parse.register_callback(self.md_parse.ParseId.FCAL_SETTINGS, self.update_ferrite_cal_status)
        self.md_parse.register_callback(self.md_parse.ParseId.FRA_VALS, self.view_fra.update)
        self.md_parse.register_callback(self.md_parse.ParseId.ERROR, self.update_view_bist_error)

        # CAMERA Handler
        self.pos_parse.register_callback(self.pos_parse.ParseId.CAM_POS, self.cam_data_handler.update_cam_data)

        # Control tab
        self.view_control.register_callback(self.view_control.ButtonId.LOOP_CAL, self.presenter.send_loop_calibrate)
        self.view_control.register_callback(self.view_control.ButtonId.LOOP_RESET, self.presenter.send_loop_cal_clear)
        self.view_control.register_callback(self.view_control.ButtonId.LOOP_CAL_VALS, self.presenter.get_loop_cal_vals)

        # This gives a callback error
        self.view_control.register_callback(self.view_control.ButtonId.LOOP_ALPHA, self._set_settings)
        self.view_control.register_callback(self.view_control.ButtonId.INFO_VERSION, self.presenter.get_fw_version)
        self.view_control.register_callback(self.view_control.ButtonId.INFO_UPDATE, self.presenter.update_gui_status)

        self.view_control.register_callback(self.view_control.ButtonId.FCAL_CAL, self.presenter.send_ferrite_calibrate)
        self.view_control.register_callback(self.view_control.ButtonId.FCAL_VALS, self.presenter.get_ferrite_cal_vals)
        self.view_control.register_callback(self.view_control.ButtonId.FCAL_SOURCE, self._set_settings)

        self.view_control.register_callback(self.view_control.ButtonId.OP_RATE, self._set_settings)

        self.view_tx_config.register_callback(self.view_tx_config.ButtonId.TX_GET, self.presenter.get_tx_config)
        self.view_tx_config.register_callback(self.view_tx_config.ButtonId.TX_SET, self._set_tx_config)
        self.view_tx_config.register_callback(self.view_tx_config.ButtonId.TX_READ, self.tx_config.file_read)
        self.view_tx_config.register_callback(self.view_tx_config.ButtonId.TX_SAVE, self.tx_config.file_save)

        # Initialize framerate  variables
        self.fps = 0.0
        self.lastupdate = time.time()

        # Updating
        # Timer interval will limit the frame rate
        # i.e. if 1ms max framerate is 1000 Hz
        #
        self.timer_interval_ms = 1
        self.timer_data_update = QtCore.QTimer()
        self.timer_data_update.timeout.connect(self._data_update)
        self.timer_data_update.start(self.timer_interval_ms)

        self.timer_plot_interval_ms = 50
        self.timer_plot_update = QtCore.QTimer()
        self.timer_plot_update.timeout.connect(self._plot_update)
        self.timer_plot_update.start(self.timer_plot_interval_ms)

        self.timer_gui_strings_interval_ms = 1000
        self.timer_gui_strings_update = QtCore.QTimer()
        self.timer_gui_strings_update.start(self.timer_gui_strings_interval_ms)

        # Show connection status label
        self.status_bar = self._main_window.get_statusbar_widget()
        self.status_bar.showMessage("Connection: {}".format(self.dialog_comms.connection_str()))
        # self._main_window.setStatusBar(self.status_bar)
        # Don't open the port until we have to as the device may be streaming data that
        # may fill a buffer that we are not ready to empty
        try:
            self.hw_interface.start()
            self.cam_zmq.start()

        except AttributeError:
            print("Hw interface not found")
            return

    def dialog_about(self):
        print(dialog_help.DialogHelp.git_version())
        dialog = dialog_help.DialogHelp()
        dialog.exec_()

    def failed(self):
        return self._failed

    # --------------------------------------------------------------------------------
    # Event handling
    # --------------------------------------------------------------------------------

    def set_harmonic_units_adc(self):
        print("set_harmonic_units_adc")
        self.actionADC_Units.setChecked(1)
        self.actionVolts_Amps.setChecked(0)
        self.set_harmonics_scaling(is_volts=False)
        self.set_harmonic_plot_labels(isVolts=False)

    def set_harmonic_units_volts(self):
        print("set_harmonic_units_volts")
        self.actionADC_Units.setChecked(0)
        self.actionVolts_Amps.setChecked(1)
        self.set_harmonics_scaling(is_volts=True)
        self.set_harmonic_plot_labels(isVolts=True)

    def set_harmonics_scaling(self, is_volts):
        print("set_harmonics_scaling")
        # Transimpedance Data handler
        gain_rx = 25.4
        gain_tx = 10.08 * 0.83
        if is_volts == True:
            trans_scaling_factor = gain_tx / gain_rx
            rx_scaling_factor = 91.55e-6 / gain_rx
            txi_scaling_factor = 91.55e-6 / gain_tx

        else:
            trans_scaling_factor = 1.0
            rx_scaling_factor = 1.0
            txi_scaling_factor = 1.0

        self.data_handle_trans.scaling_factor = trans_scaling_factor
        self.data_handle_rx.scaling_factor = rx_scaling_factor
        self.data_handle_txi.scaling_factor = txi_scaling_factor

    def _set_tx_config(self):
        self.tx_config.scale = self.view_tx_config.scale
        payload = self.tx_config.to_bytearray()
        command = md_const.PAC_ID_TX_CONFIGURATION
        self.md_tx.send_packet(command, payload)

    def _set_settings(self):
        cal_op = not self.view_control.fcal_source_is_trans
        is_accumulate = self.view_control.op_dec_and_acc
        decimation_rate = self.view_control.decimation_rate
        loop_val = self.view_control.loop_sbox

        cal_op_bytes = int.to_bytes(cal_op, 2, byteorder='big')
        if is_accumulate:
            acc_bytes = bytes([0, 1])
        else:
            acc_bytes = bytes([0, 0])

        dec_bytes = int.to_bytes(decimation_rate, 2, byteorder='big')
        loop_bytes = bytearray(struct.pack(">f", loop_val))

        print("%08X" % int.from_bytes(loop_bytes, byteorder='big'))

        payload = acc_bytes + dec_bytes + cal_op_bytes + loop_bytes
        command = md_const.PAC_ID_SETTINGS
        self.md_tx.send_packet(command, payload)

        self.update_settings((decimation_rate, is_accumulate, cal_op, loop_val))

    # --------------------------------------------------------------------------------
    # Other functions
    # --------------------------------------------------------------------------------
    def update_view_bist_error(self, error: tuple):
        print("called bist error update")
        self._sidebar.bist_error = True
        self._sidebar.error_code = error[0]

    def _update_tx_config_callback(self):
        # print("_update_tx_config_callback")
        self.view_tx_config.scale = self.tx_config.scale

        self.view_tx_config.tx_tableview.model._data = self.tx_config.get_harmonics()
        self.view_tx_config.tx_tableview.update_view(self.tx_config.get_harmonics())
        enables = self.tx_config.get_harmonic_enables_all()
        names = self.tx_config.get_harmonic_names()

        self.dhandler.update_enables(enables, names)

        self.view_vector.system_harmonics_set(self.tx_config.get_harmonic_enables_all(),
                                              self.tx_config.get_frequencies_all())
        self.view_scatter.system_harmonics_set(self.tx_config.get_harmonic_enables_all(),
                                               self.tx_config.get_frequencies_all())
        self.view_scrolling.system_harmonics_set(self.tx_config.get_harmonic_enables_all(),
                                                 self.tx_config.get_frequencies_all())
        self.view_freq.system_harmonics_set(self.tx_config.get_harmonic_enables_all(),
                                            self.tx_config.get_frequencies_all())
        self.view_pos_scatter.system_harmonics_set(self.tx_config.get_harmonic_enables_all(),
                                                   self.tx_config.get_frequencies_all())
        self.view_ssa.system_harmonics_set(self.tx_config.get_harmonic_enables_all(),
                                           self.tx_config.get_frequencies_all())
        self.view_ssa.system_harmonics_set(self.tx_config.get_harmonic_enables_all(),
                                           self.tx_config.get_frequencies_all())
        self.view_processed.system_harmonics_set(self.tx_config.get_harmonic_enables_all(),
                                           self.tx_config.get_frequencies_all())
        self.view_waterfall.system_harmonics_set(self.tx_config.get_harmonic_enables_all(),
                                           self.tx_config.get_frequencies_all())
        # Start the plotting here
        if not self.timer_plot_update.isActive():
            self.timer_plot_update.start(self.timer_interval_ms)

    def update_console_text(self, text):
        if isinstance(text, tuple):
            text = text[0]  # unpack first vale
        self.view_control.ui_console.setPlainText(text)

    def update_debug_td(self, td_sig: tuple):
        sd = np.std(td_sig[0])
        print("Time domain Std Dev:\t" + str(sd))

        ptp = np.ptp(td_sig[0])
        print("Time domain pk-pk:\t" + str(ptp))

        self.plot_debug_td.setData(td_sig)

    def update_loop_gain(self, loop_gain):
        self.view_control.loop_sbox = loop_gain

    def update_settings(self, settings: tuple):
        decimation_rate, is_accumulate, fcal_source_is_trans, loop_gain = settings
        print('Is accumulate                ' + str(is_accumulate))
        print('Decimation_rate              ' + str(decimation_rate))
        print('F.Cal Source(0=RX; 1=trans)  ' + str(fcal_source_is_trans))
        sample_rate = 97.656 / decimation_rate
        op_rate_label = "Output Rate:  " + "{:10.3f}".format(sample_rate) + " packets/second"
        print(op_rate_label)
        print("Loop gain         {}".format(loop_gain))

        self.view_control.loop_sbox = loop_gain
        self.view_control.decimation_rate = decimation_rate
        self.view_control.op_dec_and_acc = is_accumulate
        self.view_control.fcal_source_is_trans = fcal_source_is_trans

    def update_streaming_settings(self, enable_byte: tuple):
        if isinstance(enable_byte, tuple):
            enable_byte = enable_byte[0]
        print('update_streaming_settings')
        print(enable_byte[1])
        print("enable_byte:         0x%04X" %
              int.from_bytes(enable_byte, byteorder='big'))
        # convert to integer
        val = enable_byte[1]
        print(val)

        temp = {StreamingState.FCAL.name: True if (val & 1) else False,
                StreamingState.TRANS.name: True if ((val >> 1) & 1) else False,
                StreamingState.RXV.name: True if ((val >> 2) & 1) else False,
                StreamingState.TXI.name: True if ((val >> 3) & 1) else False}

        self._sidebar.streaming_select = temp

    def update_tx_enable(self, enable_byte: tuple):
        if isinstance(enable_byte, tuple):
            enable_byte = enable_byte[0]
        self._sidebar.tx_enable = True if (enable_byte[1] & 1) else False

    def update_ferrite_cal_status(self, enable_byte: tuple):
        if isinstance(enable_byte, tuple):
            enable_byte = enable_byte[0]
        self._sidebar.fcal_enable = True if (enable_byte[1] & 1) else False

    def update_nulling_status(self, enable_byte: tuple):
        if isinstance(enable_byte, tuple):
            enable_byte = enable_byte[0]
        print('update_nulling_status')
        print(enable_byte[1])
        print("enable_byte:         0x%04X" %
              int.from_bytes(enable_byte, byteorder='big'))
        # convert to integer
        val = enable_byte[1] & 3
        print(val)

        self._sidebar.null_state = val

    def _plot_update(self):
        # We pass all data to the tabs so that they can control what is plotted.
        # This avoids the need to import the controls back into main

        plot_data = self.dhandler.get_data()
        pos_data = self.cam_data_handler.get_data()

        self.view_vector.update(plot_data)
        self.view_scatter.update(plot_data)
        self.view_scrolling.update(plot_data)
        self.view_freq.update(plot_data)

        self.view_pos_scatter.update_plot(pos_data, plot_data)
        self.view_ssa.update(plot_data)
        self.view_processed.update(plot_data)
        self.view_waterfall.update(plot_data)

        self.timer_plot_update.start(self.timer_plot_interval_ms)
        # self._framerate()

    def _data_update(self):
        while True:
            self._md_log.update()
            self.detection.update(self.view_processed.line_data)

            if not self.hw_interface.messages.empty():
                self.md_parse.parse_queue(self.hw_interface.messages)
                self.pos_parse.parse_cam(self.cam_zmq.messages)
            else:
                break
            # Starts a new data timer and calls data_update again
            self.timer_data_update.start(self.timer_interval_ms)

    def quit(self):
        if 'self.hw_interface' in locals():
            self.hw_interface.stop()
        print("quit")

    def show(self):
        self._main_window.show()
        self.presenter.get_fw_version()
        self.presenter.update_gui_status()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    window = main_gui_window.MainWindow()
    main = Main(window)

    if main.failed():
        app.quit()
    else:
        main.show()
        app.exec_()

        # Tidy up the main window
        main.quit()

        # Quit the app
        app.quit()
