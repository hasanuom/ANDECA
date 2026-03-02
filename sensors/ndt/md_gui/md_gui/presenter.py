

import md_const
from md_const import NullState, StreamingState
from md_serial import MdSerialTransmit as md_tx
import time
import pyqtgraph as pg

import winsound
import record_data

class Presenter:

    def __init__(self, md_tx, md_log):
        self._md_tx = md_tx
        self._md_log = md_log

    def get_colors(self, n_points):
        color_pos = [0.0, 0.15, 0.3, 0.45, 0.60, 0.75, 1.0]
        custom_colors = [[255, 0, 0, 200], [0, 0, 255, 200], [0, 255, 0, 200], [
            10, 10, 10, 200], [255, 0, 0, 200], [0, 0, 255, 200], [0, 255, 0, 200]]
        color_map = pg.ColorMap(color_pos, custom_colors)
        return color_map.getLookupTable(start=0.0, stop=1.0, nPts=n_points, alpha=None, mode='byte')

    def update_gui_status(self):
        # self._stream_op_stop()
        # Added the sleep statements as without them some fields would not update reliably.
        # TODO: Examine the root cause
        delay = 0.1
        time.sleep(0.5)
        self.get_loop_control()
        time.sleep(delay)
        self._get_tx_enable_status()
        time.sleep(delay)
        self.get_ferrite_control()
        time.sleep(delay)
        self._get_stream_op_status()
        time.sleep(delay)
        self.get_tx_config()
        time.sleep(delay)
        self.get_settings()
        time.sleep(delay)

    def get_fw_version(self):
        self._md_tx.send_packet(md_const.PAC_ID_FW_VERS, get=True)

    def get_loop_control(self):
        self._md_tx.send_packet(md_const.PAC_ID_LOOP_CONTROL, get=True)

    def get_loop_cal_vals(self):
        self._md_tx.send_packet(md_const.PAC_ID_LOOP_CAL_VALS, get=True)

    def _get_tx_enable_status(self):
        self._md_tx.send_packet(md_const.PAC_ID_TX_ENABLE, get=True)

    def _get_stream_op_status(self):
        self._md_tx.send_packet(md_const.PAC_ID_SETTINGS_STREAMING, get=True)

    def get_td_nulling_event(self):
        self._md_tx.send_packet(md_const.PAC_ID_TIME_DOMAIN_NULL, get=True)

    def get_td_rx_event(self):
        self._md_tx.send_packet(md_const.PAC_ID_TIME_DOMAIN_RX, get=True)

    def get_td_txi_event(self):
        self._md_tx.send_packet(md_const.PAC_ID_TIME_DOMAIN_TXI, get=True)

    def get_td_tx_event(self):
        self._md_tx.send_packet(md_const.PAC_ID_TIME_DOMAIN_TX, get=True)

    def get_spectrum_tx_event(self):
        self._md_tx.send_packet(md_const.PAC_ID_SPECTRUM_TXI, get=True)

    def get_spectrum_rx_event(self):
        self._md_tx.send_packet(md_const.PAC_ID_SPECTRUM_RXV, get=True)

    # def _get_fra_event(self):
    #     self._md_tx.send_packet(md_const.PAC_ID_SFR_CONTROL, get=True)

    def get_settings(self):
        self._md_tx.send_packet(md_const.PAC_ID_SETTINGS, get=True)

    def get_tx_config(self):
        self._md_tx.send_packet(md_const.PAC_ID_TX_CONFIGURATION, get=True)

    def get_ferrite_control(self):
        self._md_tx.send_packet(md_const.PAC_ID_FERRITE_CAL_CONTROL, get=True)

    def get_ferrite_cal_vals(self):
        self._md_tx.send_packet(md_const.PAC_ID_FERRITE_CAL_VALS, get=True)

    def send_nulling_config(self, null_state: NullState) -> None:  # NOTE: For new sidebar
        if isinstance(null_state, tuple):
            null_state = null_state[0]  # unpack first value

        if null_state == md_const.NullState.ACTIVE.value:
            self.send_loop_control(md_const.PAC_CTL_NULLING_ON, md_const.PAC_CTL_NULLING_CAL_NULL)
        elif null_state == md_const.NullState.PAUSED.value:
            self.send_loop_control(md_const.PAC_CTL_NULLING_PAUSED, md_const.PAC_CTL_NULLING_CAL_NULL)
        elif null_state == md_const.NullState.ZEROED.value:
            self.send_loop_control(md_const.PAC_CTL_NULLING_CLEAR, md_const.PAC_CTL_NULLING_CAL_NULL)
        else:
            print("Invalid state - _nulling_event")
            pass

    def send_loop_calibrate(self):
        self.send_loop_control(md_const.PAC_CTL_NULLING_ON,
                               md_const.PAC_CTL_NULLING_CAL)

    def send_loop_cal_clear(self):
        self.send_loop_control(md_const.PAC_CTL_NULLING_ON,
                               md_const.PAC_CTL_NULLING_CAL_CLEAR)

    def send_loop_control(self, status_word, cal_control_word):
        payload = status_word + cal_control_word
        self._md_tx.send_packet(md_const.PAC_ID_LOOP_CONTROL,
                               payload)

    def send_fra_control(self):
        # run the fra with a payload of '0001'
        payload = '0001'
        self._md_tx.send_packet(md_const.PAC_ID_SFR_CONTROL,
                               payload)

    def send_tx_en_config(self, is_enabled: bool) -> None:  # for new sidebar
        if isinstance(is_enabled, tuple):
            is_enabled = is_enabled[0]  # unpack first value
        if is_enabled:
            self._md_tx.send_packet(md_const.PAC_ID_TX_ENABLE, '0001')
        else:
            self._md_tx.send_packet(md_const.PAC_ID_TX_ENABLE, '0000')

    def send_clear_error(self):
        self._md_tx.send_packet(md_const.PAC_ID_ERROR, payload='0000', get=False)

    def send_ferrite_calibrate(self):
        # perform a calibration
        self._md_tx.send_packet(md_const.PAC_ID_FERRITE_CAL_CONTROL, '0001')

    def send_ferrite_cal_enable(self, val: bool):  # For new Sidebar
        if isinstance(val, tuple):
            val = val[0]
        if val == True:
            self._md_tx.send_packet(md_const.PAC_ID_FERRITE_CAL_CONTROL, '0002')
        else:
            self._md_tx.send_packet(md_const.PAC_ID_FERRITE_CAL_CONTROL, '0003')

    def send_stream_config(self, stream_status):
        if isinstance(stream_status, tuple):
            stream_status = stream_status[0]

        cal_op = 1 if stream_status[StreamingState.FCAL.name] else 0
        trans = 2 if stream_status[StreamingState.TRANS.name] else 0
        rx = 4 if stream_status[StreamingState.RXV.name] else 0
        txi = 8 if stream_status[StreamingState.TXI.name] else 0

        temp = cal_op + trans + rx + txi
        payload = '%04X' % temp
        print(temp)
        self._md_tx.send_packet(md_const.PAC_ID_SETTINGS_STREAMING, payload)

    def _mark_event(self):
        duration = 175
        winsound.Beep(659, duration)
        winsound.Beep(523, duration)
        self._md_log.mark()

    def _record_event(self, is_recording):
        if isinstance(is_recording, tuple):
            temp = is_recording[0]
        # print("_record event " + str(temp[0]))
        if temp:
            self._md_log.start()
            self.get_settings()
            self.get_tx_config()
        else:
            self._md_log.stop()
