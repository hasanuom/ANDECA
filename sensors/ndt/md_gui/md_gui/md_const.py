# -*- coding: utf-8 -*-
from enum import Enum, IntEnum, auto


class NullState(Enum):
    ACTIVE = 0
    PAUSED = 1
    ZEROED = 2


class StreamingState(Enum):
    FCAL = 1
    TRANS = 2
    RXV = 3
    TXI = 4

class BIST_ERRORS:
    error = {
    "NULL_LOOP_INTEGRITY": 0xE001,
    "NULLING_SATURATION": 0xE002,
    "TXI_UNDER_CURRENT": 0xE011,
    "BIST_ERROR_TXI_OVER_CURRENT": 0xE012,
    "RXV_SIGNAL_MINIMUM": 0xE021,
    "RXV_SATURATION":   0xE022}



PAC_HEADER = bytearray(b'\xDE\x7E\xC7\xED')


PAC_ID_HARMONICS_CAL_OP = StreamingState.FCAL.value
PAC_ID_HARMONICS_TRANS  = StreamingState.TRANS.value
PAC_ID_HARMONICS_RX     = StreamingState.RXV.value
PAC_ID_HARMONICS_TXI    = StreamingState.TXI.value

PAC_ID_TIME_DOMAIN_RX   = 0x0010
PAC_ID_TIME_DOMAIN_TXI  = 0x0011
PAC_ID_TIME_DOMAIN_NULL = 0x0012
PAC_ID_TIME_DOMAIN_TX   = 0x0013


PAC_ID_SPECTRUM_RXV      = 0x0020
PAC_ID_SPECTRUM_TXI     = 0x0021


PAC_ID_FW_VERS               = 0x0080
PAC_ID_SETTINGS              = 0x0081
PAC_ID_SETTINGS_STREAMING    = 0x0082


PAC_ID_TX_CONFIGURATION      = 0x0084
PAC_ID_TX_ENABLE             = 0x0085

PAC_ID_LOOP_CAL_VALS         = 0x0086
PAC_ID_LOOP_CONTROL          = 0x0087

PAC_ID_FERRITE_CAL_VALS      = 0x0088
PAC_ID_FERRITE_CAL_CONTROL    = 0x0089

PAC_ID_SFR_VALS         = 0x008A
PAC_ID_SFR_CONTROL      = 0x008B


PAC_ID_ERROR = 0x00E0


PAD_ID_MARK = 0x3000


PAC_CTL_NULLING_ON        = '{:04X}'.format(NullState.ACTIVE.value)
PAC_CTL_NULLING_PAUSED    = '{:04X}'.format(NullState.PAUSED.value)
PAC_CTL_NULLING_CLEAR     = '{:04X}'.format(NullState.ZEROED.value)


PAC_CTL_NULLING_CAL_NULL  = '0000'  # don't calibrate
PAC_CTL_NULLING_CAL       = '0001'
PAC_CTL_NULLING_CAL_CLEAR = '0002'





PAC_CMD_GET_MASK         = 0xC000
PAC_CMD_SET_MASK         = 0x8000


class DataStreamingConst:
    names = ['cal_op', 'trans', 'rxv', 'txi']
