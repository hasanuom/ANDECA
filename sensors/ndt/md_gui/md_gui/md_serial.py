# -*- coding: utf-8 -*-
"""
Created on Wed Aug 21 10:00:37 2019

@author: h43191kb

"""

import md_const
import md_packet


class MdSerialTransmit():
    def __init__(self, hwinterface):
        self.hwinterface = hwinterface
        self._next_seq = 0

    def send_packet(self, command: int, payload=b'', get: bool = False):
        if get:
            command = command | md_const.PAC_CMD_GET_MASK
        else:
            command = command | md_const.PAC_CMD_SET_MASK

        if isinstance(command, int):
            pass
        elif isinstance(command, bytes):
            raise Exception("Command should not be in bytes")

        if isinstance(payload, str):
            payload_bytes = bytes.fromhex(payload)
        else:
            payload_bytes = payload

        packet = md_packet.MdPacket(address=0, command=command, seq_num=self._next_seq, payload=payload_bytes)
        data = packet.generate_packet()

        print('Transmit command 0x{:04X}'.format(command))

        self._next_seq += 1
        self.hwinterface.write_data(data)





