"""Packet ID and mask definitions ported from pac_id.h.

The numeric values here are examples.  Replace them with the real constants
from your C header if you have access to it; the script will still work as
long as host and device agree on the numbers.
"""

# masks applied to command field
GET_MASK  = 0x8000  # command | GET_MASK means "read"
SET_MASK  = 0x0000  # command | SET_MASK means "write" (usually the same as
                    # clear bit 15)

# basic packet IDs (example values)
PAC_ID_FW_VERS            = 0x0001
PAC_ID_SETTINGS           = 0x0002
PAC_ID_SETTINGS_STREAMING = 0x0003
PAC_ID_TX_CONFIGURATION   = 0x0010
PAC_ID_TX_ENABLE          = 0x0011
PAC_ID_LOOP_CONTROL       = 0x0012
PAC_ID_LOOP_CAL_VALS      = 0x0013
PAC_ID_FERRITE_CAL_CONTROL= 0x0020
PAC_ID_FERRITE_CAL_VALS   = 0x0021
PAC_ID_ERROR              = 0x00FF

# data acquisition packets
PAC_ID_TIME_DOMAIN_RX     = 0x0100
PAC_ID_TIME_DOMAIN_TXI    = 0x0101
PAC_ID_TIME_DOMAIN_NULL   = 0x0102
PAC_ID_TIME_DOMAIN_TX     = 0x0103
PAC_ID_SPECTRUM_RX        = 0x0200
PAC_ID_SPECTRUM_TXI       = 0x0201

# streaming harmonic packets (sent periodically)
PAC_ID_HARMONICS_CAL_OP   = 0x0300
PAC_ID_HARMONICS_TRANS    = 0x0301
PAC_ID_HARMONICS_RX       = 0x0302
PAC_ID_HARMONICS_TXI      = 0x0303

# additional IDs used by the firmware; add more as needed

# helper for making an "address zero" packet to the sensor
DEFAULT_DEVICE_ADDRESS = 0
