# Camera constants
# Adam 02/11/2022

from enum import Enum

class CamMessage(Enum):
    CAM_INIT = 1
    CAM_POS = 2
    CAM_STATE = 3
    CAM_ERROR = 4
    CAM_FINDHEAD = 5
    CAM_FINDTAG = 6

class CamError(Enum):
    CAM_ERR_INIT = 1
    CAM_ERR_MEM = 2
    CAM_ERR_NOTREADY = 3

CAM_HEADER = bytearray(b'\xF0\x0D\xBA\x11')

class CamDataConst:
    names = ['x_data', 'y_data', 'z_data']