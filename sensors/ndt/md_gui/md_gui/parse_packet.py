
import md_const
from cam_const import CamMessage, CamDataConst
import numpy as np
import struct
import collections
import pandas as pd
import os
from tabulate import tabulate
from callback_list import CallbackList
from enum import Enum, auto, unique

class ParsePacket(CallbackList):
    @unique
    class ParseId(Enum):
        FW_VERSION = auto()
        STREAM_FCAL = auto()
        STREAM_TRANS = auto()
        STREAM_RXV = auto()
        STREAM_TXI = auto()
        TIME_DOMAIN = auto()
        SPECTRUM = auto()
        SETTINGS = auto()
        STREAM_SETTINGS = auto()
        FCAL_SETTINGS = auto()
        LOOP_SETTINGS = auto()
        FERRITE_CAL_VALS = auto()
        LOOP_CAL_VALS = auto()
        FRA_VALS = auto()
        ERROR = auto()
        TX_ENABLE = auto()
        TX_CONFIG = auto()
        CAM_INIT = auto()
        CAM_POS = auto()
        CAM_STATE = auto()
        CAM_ERROR = auto()
        CAM_FINDHEAD = auto()
        CAM_FINDTAG = auto()

    def __init__(self, queue_rx, tx_config, parent=None):
        super().__init__()
        self.is_data_new = False
        self.rxOpStr = "Init"
        self.td_sig = [0] * 1024
        self.tx_config = tx_config
        self.handlers = collections.defaultdict(list)

        # Initialise all call arguments to None
        self._call_args = dict()
        for item in self.ParseId:
            self._call_args[item.name] = None

    #
    # Get single packet from the queue
    #
    def parse_queue(self, queue_rx):
        if not queue_rx.empty():
            pac = queue_rx.get()

            # print('Parse pac.command 0x{:04X}'.format(pac.command))
            if pac.command == md_const.PAC_ID_FW_VERS:
                text = self._parse_firmwareVersion(pac)
                self.call_callback(self.ParseId.FW_VERSION, (text,))

            elif pac.command == md_const.PAC_ID_HARMONICS_CAL_OP:
                print('MD packet: ', pac.payload)

            elif pac.command == md_const.PAC_ID_HARMONICS_TRANS:
                data = self._parse_harmonics(pac)
                id = md_const.DataStreamingConst.names[1]
                self.call_callback(self.ParseId.STREAM_TRANS, (id, data))

            elif pac.command == md_const.PAC_ID_HARMONICS_RX:
                data = self._parse_harmonics(pac)
                id = md_const.DataStreamingConst.names[2]
                self.call_callback(self.ParseId.STREAM_RXV, (id, data))

            elif pac.command == md_const.PAC_ID_HARMONICS_TXI:
                data = self._parse_harmonics(pac)
                id = md_const.DataStreamingConst.names[3]
                self.call_callback(self.ParseId.STREAM_TXI, (id, data))

            elif pac.command == md_const.PAC_ID_TIME_DOMAIN_NULL or \
                pac.command == md_const.PAC_ID_TIME_DOMAIN_RX or    \
                pac.command == md_const.PAC_ID_TIME_DOMAIN_TXI or   \
                pac.command == md_const.PAC_ID_TIME_DOMAIN_TX:
                print('Packet Received TIME_DOMAIN')
                self.td_sig = self._parse_td_payload(pac)
                self.call_callback(self.ParseId.TIME_DOMAIN, (self.td_sig,))

            elif pac.command == md_const.PAC_ID_SPECTRUM_RXV or \
                 pac.command == md_const.PAC_ID_SPECTRUM_TXI:
                print('Packet Received SPECTRUM')
                self.spectrum = self._parse_spectra_payload(pac)
                self.call_callback(self.ParseId.SPECTRUM, (self.spectrum, ))

            elif pac.command == md_const.PAC_ID_SETTINGS:
                print('Packet Received PAC_ID_SETTINGS')
                is_accumulate, decimation_rate, cal_select, loop_gain = struct.unpack('>HHHf', pac.payload)
                is_accumulate =  bool(is_accumulate == 1) # force boolean
                self.call_callback(ParsePacket.ParseId.SETTINGS, (decimation_rate, is_accumulate, cal_select, loop_gain))

            elif pac.command == md_const.PAC_ID_SETTINGS_STREAMING:
                print('Packet Received PAC_ID_OP_SETTINGS_STREAMING')
                self.call_callback(self.ParseId.STREAM_SETTINGS, (pac.payload[0:2],))

            elif pac.command == md_const.PAC_ID_LOOP_CONTROL:
                print('Packet Received PAC_ID_LOOP_CONTROL')
                #print(pac.payload[0:2])
                self.call_callback(self.ParseId.LOOP_SETTINGS, (pac.payload[0:2],))

            elif pac.command == md_const.PAC_ID_TX_ENABLE:
                print('Packet Received PAC_ID_TX_ENABLE')
                #print(pac.payload[0:2])
                self.call_callback(self.ParseId.TX_ENABLE, (pac.payload[0:2],))

            elif pac.command == md_const.PAC_ID_FERRITE_CAL_CONTROL:
                print('Packet Received PAC_ID_OP_FERRITE_CAL_STATUS')
                #print(pac.payload[0:2])
                self.call_callback(self.ParseId.FCAL_SETTINGS, (pac.payload[0:2],))

            elif pac.command == md_const.PAC_ID_TX_CONFIGURATION:
                print('Packet Received PAC_ID_TX_CONFIGURATION')
                self._parse_tx_config(pac)

            elif pac.command == md_const.PAC_ID_LOOP_CAL_VALS:
                print('Packet Received PAC_ID_LOOP_CAL_VALS')
                text = self._parse_loop_phase_cal(pac)
                self.call_callback(ParsePacket.ParseId.LOOP_CAL_VALS, (text,))

            elif pac.command == md_const.PAC_ID_SFR_VALS:
                print('Packet Received PAC_ID_SFR_VALS')
                text = self._parse_payload_fra(pac)
                self.call_callback(ParsePacket.ParseId.FRA_VALS, (text,))

            elif pac.command == md_const.PAC_ID_FERRITE_CAL_VALS:
                print('Packet Received PAC_ID_FERRITE_CAL_VALS')
                text = self._parse_ferrite_cal_values(pac)
                self.call_callback(ParsePacket.ParseId.FERRITE_CAL_VALS, (text,))

            elif pac.command == md_const.PAC_ID_ERROR:
                print('Packet Received PAC_ID_ERROR')
                text = self._parse_error(pac)
                self.call_callback(ParsePacket.ParseId.ERROR, (text,))

            else:
                print('******************************')
                print('Unknown packet received  - command {0:#X}'.format(int(pac.command)))
                print("{0:#X}".format(int(pac.payload[0])))
                print('******************************\n')

            del pac

    def parse_cam(self, queue_cam):
        if not queue_cam.empty():
            pac = queue_cam.get()
            if pac.command == CamMessage.CAM_INIT.value:
                print('cam init')
            elif pac.command == CamMessage.CAM_POS.value:
                text = self._parse_cam_pos(pac)
                self.call_callback(ParsePacket.ParseId.CAM_POS, (text,))

            elif pac.command == CamMessage.CAM_STATE.value:
                print('cam state')
            elif pac.command == CamMessage.CAM_ERROR.value:
                print('cam error')
            elif pac.command == CamMessage.CAM_FINDHEAD.value:
                print('cam find head')
            elif pac.command == CamMessage.CAM_FINDTAG.value:
                print('cam find tag')

            else:
                print('******************************')
                print('Unknown packet received  - command {0:#X}'.format(int(pac.command)))
                print("{0:#X}".format(int(pac.payload[0])))
                print('******************************\n')

            del pac

    def _parse_cam_pos(self, pac):

        p = struct.unpack("!hhh", pac.payload)
        x, y, z = [m / 100 for m in p]

        seq_num = int.from_bytes(pac.seq_num, byteorder='big')

        pos_data = {'seq_num': seq_num, CamDataConst.names[0]: x,
                    CamDataConst.names[1]: y,
                    CamDataConst.names[2]: z}

        return pos_data

    def _parse_error(self, pac):
        error_code = int.from_bytes(pac.payload[0: 2], byteorder='big')
        error_str ="{0:#x}".format(error_code)
        #print("error code {0}".format(error_str))
        cstr = "Unknown error code"
        for key, value in md_const.BIST_ERRORS.error.items():
            if value == error_code:
                cstr = str(key)

        error_str ="{0:#x}\n{1}".format(error_code, cstr)
        return error_str


    def _parse_tx_config(self, pac):
        #print("parse_tx_config")

        #print(pac.nbytes_payload)

        offset = 0
        self.tx_config.mask = pac.payload[offset: offset + 2]
        offset += 2
        scale = struct.unpack('>f', pac.payload[offset: offset + 4])
        # struct.unpack always returns a tuple; even for a single value. Therefore [0] is required
        self.tx_config.scale = scale[0]

        offset += 4

        n_remaining = pac.nbytes_payload - offset

        n_bytes_per_freq = 10
        n_tx_freq = n_remaining // n_bytes_per_freq

        for i in range(n_tx_freq):
        #while n_remaining > 0:
            #print(offset)
            self.tx_config.set_harmonic_freq(i, int.from_bytes(pac.payload[offset : offset + 2], byteorder='big'))
            offset += 2
            self.tx_config.set_harmonic_magnitude(i, struct.unpack('>f', pac.payload[offset: offset + 4])[0])
            offset += 4
            self.tx_config.set_harmonic_phase(i, struct.unpack('>f', pac.payload[offset: offset + 4])[0])
            offset += 4

         #   n_remaining -= 10;
          #  i +=1

        if(0):
            self.tx_config.print_tx_config()



    def _parse_loop_phase_cal(self, pac):
        phase_cal = {'n_vals': 0, 'harmonic_freq': [], 'data': []}
        raw_cal = {'n_vals': 0, 'harmonic_freq': [], 'data': []}

        offset = 0
        n_vals = int.from_bytes(pac.payload[offset: offset + 2], byteorder='big')
        offset += 2

        phase_cal['n_vals'] = n_vals
        raw_cal['n_vals'] = n_vals

        offset = self._parse_harmonic_freq_complex_data(pac, offset, n_vals, phase_cal)
        offset = self._parse_harmonic_freq_complex_data(pac, offset, n_vals, raw_cal)

        op_str = self._parse_harmonic_freq_print(phase_cal, 'Loop Phase Calibration')
        self._parse_harmonic_freq_print(raw_cal, 'Loop Phase Calibration (Raw)')

        return op_str


    def _parse_ferrite_cal_values(self, pac):
        cal = {'n_vals': 0, 'harmonic_freq': [], 'data': []}

        offset = 0
        n_vals = int.from_bytes(pac.payload[offset: offset + 2], byteorder='big')
        offset += 2

        cal['n_vals'] = n_vals
        offset = self._parse_harmonic_freq_complex_data(pac, offset, n_vals, cal)
        op_str = self._parse_harmonic_freq_print(cal, 'Ferrite Cal. Values')

        print(op_str)
        return op_str


    #
    # 
    def _parse_firmwareVersion(self, pac):
        self.rxOpStr = "".join(map(chr, pac.payload))

        print(self.rxOpStr)
        return self.rxOpStr



    # Middle endian
    # The TI DSP is actually little endian at greater than 16-bits granularity. 
    # However each 16-bits is stored big endian. 
    # For example floating point numbers come out as two 16-bits with the first 16-bits being the least significant 
    # i.e. little endian at a 16-bit word level. 
    # Looks like Honeywell 316 endian See https://wiki2.org/en/Endianness#Middle-endian 
    # For confirmation see https://e2e.ti.com/support/microcontrollers/c2000/f/171/t/152372 
    #
    # type np.float32 is little endian
    #
    def _parse_harmonics(self, pac):

        pac_len = len(pac.payload)

        if (pac_len % 8 != 0):
            print("Error - payload invalid size  "  + os.path.basename(__file__))
            return

        # re = list(itertools.chain.from_iterable([pac.payload[i:i + 4] for i in range(0, pac_len, 8)]))
        # im = [pac.payload[i:i + 4] for i in range(4, pac_len, 8)]
        real_bytes = bytearray(0)
        imag_bytes = bytearray(0)
        # Data is of type 'float'
        # data is real, imag, real, imag ...
        #print(self.bytes_to_float_vector(pac.payload))

        for i in range (0, pac_len, 8):
            lsword = pac.payload[i   : i + 2]
            word = pac.payload[i+2 : i + 4] + lsword  # big endian
            real_bytes = real_bytes + word[::-1]  # reverse here for little endian

            lsword = pac.payload[i + 4 : i + 6]
            word = pac.payload[i + 6 : i + 8] + lsword
            imag_bytes = imag_bytes + word[::-1] 

        x_data = self._bytes_to_float_vector(real_bytes)
        y_data = self._bytes_to_float_vector(imag_bytes)

        seq_num = int.from_bytes(pac.seq_num, byteorder='big')
        harmonic_data = {'seq_num': seq_num, 'x_data': x_data, 'y_data': y_data}

        return harmonic_data

    def chunks(lst, n):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]


    def _parse_td_payload(self, pac):
        if len(pac.payload) == (1024 * 4) : # float
            tdata =  self._parse_floats(pac.payload)
        else:                               # uint16_t
            fmt = ">%dH" % (len(pac.payload) // 2)
            tdata = np.array(struct.unpack(fmt, pac.payload))
        return tdata

    def _parse_spectra_payload(self, pac):
        '''
            Output buffer structure:
            OutBuf[0] = real[0]           // DC value
            OutBuf[1] = real[1]
            OutBuf[2] = real[2]
            ………
            OutBuf[N/2] = real[N/2]       // Nyquist frequency value
            OutBuf[N/2+1] = imag[N/2-1]
            ………
            OutBuf[N-3] = imag[3]
            OutBuf[N-2] = imag[2]
            OutBuf[N-1] = imag[1]

        '''
        
        N = 1024
        # Use this scaling factor to get to ADC units
        # The quirks of the RFFT mean that the DC and nyquist bins have a different scaling 
        # As the MD does prescaling the magnitude is correct, for ADC units, for all bins except
        # the DC an nyquist bins
        dc_nyquist_sf = 0.5
        
        # As the ADC input is biased to 1/2 input range can factor this in 
        # to give the actual DC input 
        expected_dc_value = 65536/2

        spectrum = np.ndarray(N//2, dtype=complex)
        
        if len(pac.payload) == (1024 * 4):
            data = self._parse_floats(pac.payload)
            # print(data['data'])

            for i in range((N//2)-1):
                if i == 0:
                    # DC bin
                    spectrum[0] = complex(data[0], 0) * dc_nyquist_sf
                    spectrum[0] = spectrum[0] - complex(expected_dc_value, 0)
                else:
                    spectrum[i] = complex(data[i], data[N-i])
            
            # NYQUIST BIN????
            spectrum[N//2-1] = complex(data[512], 0) *dc_nyquist_sf

        #print('length spectrum = {}'.format(len(spectrum)))

        BW = 85 # harmonics
        # ignore DC bin
        z = spectrum[1:BW]
        Vavg = np.mean(abs(z))
        Vrms = np.sqrt(np.mean(z * np.conj(z)))
        print("Spectrum voltage in {:.2f} Bandwidth".format(BW))
        print("Vavg:\t{:.3}\nVrms\t{:.3}\n".format(Vavg, Vrms))

        return spectrum



    def _parse_payload_fra(self, pac):
        rxv = {'n_vals': 0, 'harmonic_freq': [], 'data': []}
        txi = {'n_vals': 0, 'harmonic_freq': [], 'data': []}

        offset = 0
        n_vals = int.from_bytes(pac.payload[offset: offset + 2], byteorder='big')
        offset += 2

        rxv['n_vals'] = n_vals
        txi['n_vals'] = n_vals

        offset = self._parse_harmonic_freq_complex_data(pac, offset, n_vals, rxv)
        offset = self._parse_harmonic_freq_complex_data(pac, offset, n_vals, txi)

        self._parse_harmonic_freq_print(rxv, 'RXV values')
        self._parse_harmonic_freq_print(txi, 'TXI values')
        return [rxv, txi]



    def _parse_harmonic_freq_complex_data(self, pac, offset, n, data):

        for i in range(n):

            #  Skip over the harmonic freq values
            temp = int.from_bytes(pac.payload[offset: offset + 2], byteorder='big')
            data['harmonic_freq'].append(temp)
            offset += 2

            d = struct.unpack('>ff', pac.payload[offset: offset + 8])
            data['data'].append(complex(d[0], d[1]))
            offset += 8

        data['data'] = np.array(data['data'])
        return offset



    def _parse_harmonic_freq_print(self, data, title: str):
        d = data.get('data')
        rdata = {'harmonic_freq': data.get('harmonic_freq'),
                 'real': np.real(d),
                 'imag': np.imag(d),
                 'mag': np.abs(d),
                 'phase': np.angle(d)}

        fstr = '\n\n--------------   {title}  -------------\n'.format(title=title)
        fstr += "Number of Calibration Points:  " + str(data.get('n_vals')) + '\n'
        df = pd.DataFrame(data=rdata)
        fstr += tabulate(df, headers='keys', tablefmt='psql')
        print(fstr)
        return fstr



    def _parse_floats(self, payload):

        pac_len = len(payload)
        if pac_len % 4 != 0:
            print("Error - payload invalid size  "  + os.path.basename(__file__))
            return

        bigendian = bytearray(0)
        for i in range (0, pac_len, 4):
            lsword = payload[i   : i + 2]
            word = payload[i+2 : i + 4] + lsword  # big endian
            bigendian += word

        data = np.array(struct.unpack(f">{pac_len//4}f", bytes(bigendian)))
        return data

    @staticmethod
    def _bytes_to_float_vector(byte_array):
        temp = np.frombuffer(byte_array, dtype=np.float32)
        return temp



