"""Packet ID and mask definitions ported from pac_id.h.

The numeric values here are examples.  Replace them with the real constants
from your C header if you have access to it; the script will still work as
long as host and device agree on the numbers.
"""

# masks applied to command field
# these match the C macros in pac_id.h
GET_MASK  = 0xC000  # high two bits set indicates a "get" operation
SET_MASK  = 0x8000  # high bit set indicates a "set" (write) operation

# packet ID values copied from pac_id.h
PAC_ID_HARMONICS_CAL_OP         = 0x0001
PAC_ID_HARMONICS_TRANS          = 0x0002
PAC_ID_HARMONICS_RX             = 0x0003
PAC_ID_HARMONICS_TXI            = 0x0004

PAC_ID_TIME_DOMAIN_RX           = 0x0010
PAC_ID_TIME_DOMAIN_TXI          = 0x0011
PAC_ID_TIME_DOMAIN_NULL         = 0x0012
PAC_ID_TIME_DOMAIN_TX           = 0x0013

PAC_ID_SPECTRUM_RX              = 0x0020
PAC_ID_SPECTRUM_TXI             = 0x0021

PAC_ID_FW_VERS                  = 0x0080
PAC_ID_SETTINGS                 = 0x0081
PAC_ID_SETTINGS_STREAMING       = 0x0082

PAC_ID_TX_CONFIGURATION         = 0x0084
PAC_ID_TX_ENABLE                = 0x0085

PAC_ID_LOOP_CAL_VALS            = 0x0086
PAC_ID_LOOP_CONTROL             = 0x0087

PAC_ID_FERRITE_CAL_VALS         = 0x0088
PAC_ID_FERRITE_CAL_CONTROL      = 0x0089

PAC_ID_SFR_VALS                 = 0x008A
PAC_ID_SFR_CONTROL              = 0x008B

PAC_ID_ERROR                    = 0x00E0

# (values above already cover the acquisition and harmonic IDs.)
# there is no need for duplicate entries; they're listed earlier.

# additional IDs used by the firmware; add more as needed

# helper for making an "address zero" packet to the sensor
DEFAULT_DEVICE_ADDRESS = 0
