class MdPacket(object):
    '''
    classdocs
    '''

    def __init__(self, address: int, command: int, seq_num: int, payload: bytearray, nbytes_payload: int = 0,
                 header=None):
        '''
        Constructor
        '''

        self.mod_val = 2 ** 16
        self.max_val = 2 ** 16 - 1

        self.payload = payload
        self.command = command
        self.address = int.to_bytes(address, 2, byteorder='big')
        self.seq_num = int.to_bytes(seq_num, 2, byteorder='big')

        if header is not None:
            self.header = header
        else:
            self.header = bytearray(b'\xDE\x7E\xC7\xED')

        self.nbytes_payload = nbytes_payload
        self.checksum = 0xFAFA
        self.isValid = False  # for Received packets - passed CRC check?
        self.isTimeout = False  # for Received packets - did timeout occur

    def print_input(self):
        print(self.Vin_Min)

    def generate_packet(self):
        self.nbytes_payload = len(self.payload).to_bytes(2, byteorder='big')
        self._calc_checksum(is_check=False)
        packet = self._concat_packet()
        return packet

    def _calc_checksum(self, is_check: bool):
        # check or generate a checksum

        retval = True

        if is_check:
            checksum = int.from_bytes(self.checksum, byteorder='big')
        else:
            checksum = 0

        checksum += int.from_bytes(self.address, byteorder='big')
        # checksum += int.from_bytes(self.command, byteorder='big')
        checksum += self.command

        checksum += int.from_bytes(self.seq_num, byteorder='big')

        nbytes_payload = int.from_bytes(self.nbytes_payload, byteorder='big')
        checksum += nbytes_payload

        # Cycle through payload
        for i in range(0, nbytes_payload, 2):
            checksum += int.from_bytes(self.payload[i: i + 2], byteorder='big')

        checksum = checksum % self.mod_val

        if is_check:
            if checksum == 0:
                retval = True
            else:
                print("failed checksum")
                self.packet_print_fields()
                retval = False
        else:
            ones_comp = (~checksum) & self.max_val
            twos_comp = (ones_comp + 1) % self.mod_val
            self.checksum = twos_comp.to_bytes(2, byteorder='big')
            # print("sum  " + '%04X' % sum)
            # print("twos   0x" + '%02X' % twos_comp)
            # print("self.checksum = 0x", self.checksum.hex())
        return retval

    def calc_crc_bad(self):
        return bytes.fromhex('FAFA')

    def _concat_packet(self):
        temp = self.header + self.address + int.to_bytes(self.command, 2, 'big') + self.seq_num \
               + self.nbytes_payload + self.payload + self.checksum
        return temp

    def print_packet(self):
        temp = "".join("0x{:02X} ".format(x) for x in self._concat_packet())
        print(temp)
        self.packet_print_fields()

    def packet_print_fields(self):
        print("header:         0x%04X" % int.from_bytes(self.header, byteorder='big'))
        print("address:        0x%04X" % int.from_bytes(self.address, byteorder='big'))
        print("command:        0x%04X" % int.from_bytes(self.command, byteorder='big'))
        print("seq_num:            %d" % int.from_bytes(self.seq_num, byteorder='big'))
        print("nbytes_payload:     %d" % int.from_bytes(self.nbytes_payload, byteorder='big'))
        print("checksum:       0x%04X" % int.from_bytes(self.checksum, byteorder='big'))
