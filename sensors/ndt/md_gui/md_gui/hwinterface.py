import zmq
import threading
import queue
import struct
import serial
import time
import sys
import glob
from md_packet import MdPacket
from PyQt5.QtCore import QObject


class HwInterface(QObject):
    def __init__(self):
        super().__init__()

        # Queue for message dictionary
        self.messages = queue.Queue()

        # Queue for binary log messages
        self.message_log = queue.Queue()

        self._allow_fixed_csum = False

        self.thr_read = None
        self._execute_n = threading.Event()

        self.is_read_enable = True

    @property
    def allow_fixed_csum(self):
        return self._allow_fixed_csum

    @allow_fixed_csum.setter
    def allow_fixed_csum(self, v):
        self._allow_fixed_csum = v

    def start(self):
        self._execute_n.clear()
        self.thr_read = threading.Thread(target=self._read_thread)
        self.thr_read.setDaemon(True)
        self.thr_read.start()

    def _read_thread(self):
        print("[I] Started Read Thread")

        while not self._execute_n.isSet():
            if not self._read_thread_loop():
                break

    def _read_thread_loop(self):
        return self.is_read_enable

    def write_data(self, data):
        pass

    def close(self):
        pass

    def stop(self):
        self.set_read_enable(False)
        time.sleep(1)
        self.close()

    def set_read_enable(self, val):
        self.is_read_enable = val

    def get_read_enable(self):
        return self.is_read_enable

    def stopped(self):
        return self.thr_read.is_alive()


class HwInterfaceSerial(HwInterface):
    _instance = None
    STARTWORD = 0xDE7EC7ED
    STARTWORD_BYTES = int.to_bytes(STARTWORD, 4, byteorder='big')
    STARTWORD_INT = [x for x in STARTWORD_BYTES]


    def __init__(self, comport='com6', baudrate=1e6):
        super().__init__()

        print('Creating Serial interface')
        #print(self.STARTWORD_BYTES.hex())


        if self._instance is not None:
            self._instance.close()
            while self._instance.is_open():
                pass

        self._instance = serial.Serial()  # called with no arguments
        self._instance.baudrate = baudrate
        self._instance.port = comport

        try:
            self._instance.open()
        except serial.SerialException:
            print("Error opening serial port - invalid parameters")
            self._instance = None
            return

        time.sleep(.2)
        self._instance.flush()

        self._csum = 0
        self._buf = ''
        self._bufidx = 0

    def __str__(self):
        return (f'{self.__class__.__name__}('
                f'{self._instance.port!r}, '
                f'{self._instance.baudrate!r} Baud)')

    @staticmethod
    def serial_port_list():
        """ Lists serial port names

            :raises EnvironmentError:
                On unsupported or unknown platforms
            :returns:
            A list of the serial ports available on the system
        """
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result

    def write_data(self, data):
        if self._instance is None:
            print("Serial port - not configured")
            return

        if self._instance.isOpen():
            # self.__instance.write_timeout(1)
            print(f"Send Data: ", end="")
            for byte in data:
                print(f"{byte:02X} ", end="")
            print()
            self._instance.write(data)
            self._instance.flush()
        # print("Writing data", data)
        return

    def _read_thread_loop(self):
        ii = 3
        while ii >= 0:
            b = self._get_byte()
            # print(f"{ii} => 0x{b:02X}")
            if b != ((self.STARTWORD >> 8 * ii) & 0xFF):
                ii = 3
            else:
                ii -= 1

        # print("Received STARTWORD")
        # log file needs an 8 byte timestamp

        ts_us = int(time.time_ns() // 1000)
        ts_bytes_alt = struct.pack('!Q', ts_us)
        self.packet_bytes = [x for x in ts_bytes_alt]
        self.packet_bytes += self.STARTWORD_INT
        self._csum = 0

        address, temp = self._get_word()
        self.packet_bytes += temp
        cmd,temp = self._get_word()
        self.packet_bytes += temp
        seq, temp = self._get_word()
        self.packet_bytes += temp
        length, temp = self._get_word()
        self.packet_bytes += temp

        # Sanity check length
        if length > 6144:
            return True

        # print(f"Address = {address}")
        # print(f"Command = {cmd}")
        # print(f"Sequence = {seq}")
        # print(f"length = {length}")
        # print(f"Number of data bytes {length}")

        # data = list()
        data = bytearray()
        for ii in range(length // 2):
            a = self._get_byte()
            b = self._get_byte()
            data.append(a)
            data.append(b)
            self._csum_two_bytes(a, b)

        self.packet_bytes += data

        # for ii in range(length//2):
        # 	word = self._get_word()
        # 	bytes = struct.pack("H", word)
        # 	data.append(bytes[1])
        # 	data.append(bytes[0])
        # print(data)

        checksum, temp = self._get_word()
        self.packet_bytes += temp

        # throw away any overflow bits from checksum
        self._csum %= 65536
        if self._csum != 0 and (not self._allow_fixed_csum or self._csum != 0xFAFA):
            print(
                f"Bad CRC: Expected 0x{self._csum:04X} ; "
                f"Recieved 0x{checksum:04X}\n"
                f"(ID = 0x{cmd:04X}, "
                f"Length = {length})")
        else:
            # print("Message Received")
            self.message_log.put(self.packet_bytes)
            self.messages.put(MdPacket(command=cmd, payload=data, address=address, seq_num=seq, nbytes_payload=length))

        # Tell the loop to keep looping
        return self.get_read_enable()

    def __read(self):
        # while len(b) == 0:
        # 	#b = self.__instance.read(256)
        # 	b = self.__instance.read(2)
        while not self.is_read_enable:
            pass

        b = self._instance.read(2)

        self._buf = b
        self._bufidx = 0

    def _get_byte(self) -> int:
        if self._bufidx == len(self._buf):
            self.__read()

        b = self._buf[self._bufidx]
        self._bufidx += 1
        # print(b)
        return b

    def _get_word(self) -> int:
        a = self._get_byte()
        b = self._get_byte()
        word = a << 8
        word |= b
        self._csum += word
        return word, [a,b]

    def _csum_two_bytes(self, a, b):
        word = a << 8
        word |= b

        self._csum += word
        return word

    def close(self):
        if self._instance is not None:
            self._instance.close()


class HwInterfaceZMQ(HwInterface):

    def __init__(self, host="192.168.1.5", dataport=5001, commandport=5101, stateport=5201, context=None, header=None):
        super().__init__()

        print('Creating ZMQ interface')

        self._context = context or zmq.Context.instance()

        if header is not None:
            self._header = header
        else:
            # set default packet header to MD header
            self._header = bytearray(b'\xDE\x7E\xC7\xED')

        self._host = host
        self._dataport = dataport
        self._cmdport = commandport
        self._stateport = stateport

        self._sockData = self._context.socket(zmq.SUB)
        self._sockData.setsockopt(zmq.SUBSCRIBE, b"")
        self._sockState = self._context.socket(zmq.SUB)
        self._sockState.setsockopt(zmq.SUBSCRIBE, b"")
        self._sockCommand = self._context.socket(zmq.REQ)

        self._poller = zmq.Poller()
        self._poller.register(self._sockData, zmq.POLLIN)
        self._poller.register(self._sockState, zmq.POLLIN)

    def __str__(self):
        return (f'{self.__class__.__name__}('
                f'{self._host!r}, '
                f'dataport(rx) = {self._dataport!r}, '
                f'command_port(tx) = {self._cmdport!r}), '
                f'state_port(rx) = {self._stateport!r})\n')

    def start(self):
        self._sockData.connect(f"tcp://{self._host:s}:{self._dataport:d}")
        self._sockCommand.connect(f"tcp://{self._host:s}:{self._cmdport:d}")
        self._sockState.connect(f"tcp://{self._host:s}:{self._stateport:d}")

        print("[I] Connected sockets")
        super().start()

    def _read_thread_loop(self):
        socks = dict(self._poller.poll(timeout=1))

        if self._sockData in socks and socks[self._sockData] == zmq.POLLIN:
            data = self._sockData.recv()
            msg = self._make_message(data)
            self.messages.put(msg)
            self.message_log.put(data)

        if self._sockState in socks and socks[self._sockState] == zmq.POLLIN:
            data = self._sockState.recv()
            msg = self._make_message(data)
            self.messages.put(msg)
            self.message_log.put(data)

        # Tell the loop to keep looping
        return True

    def write_data(self, data):
        print("Writing data\t", data)
        self._sockCommand.send(b"\x00" * 8 + data)

        resp = self._sockCommand.recv()
        msg = self._make_message(resp)

        # 0x7FFF is a dummy acknowledgement
        if msg.command != 0x7FFF:
            assert msg.isValid
            self.messages.put(msg)
            self.message_log.put(resp)

    def _make_message(self, data):
        timestamp, start, address, command, sequence, length = struct.unpack("!QIHHHH", data[:20])
        databytes = data[20:-2]
        assert (len(databytes) == length)
        datawords = struct.unpack(f"!{length // 2}H", databytes)

        msgcrc = struct.unpack("!H", data[-2:])[0]
        crc = address + command + sequence + length + sum(datawords) + msgcrc

        # throw away any overflow bits from checksum
        crc %= 65536

        # TODO: does this need to include the header? - If you want camera data then yes
        pac = MdPacket(command=command, payload=databytes, address=address, seq_num=sequence, nbytes_payload=length, header=self._header)


        if command != 0x7FFF:
            # assert ((crc & 0xFFFF) == 0 or (self._allow_fixed_csum and msgcrc == 0xFAFA))
            if (crc & 0xFFFF) == 0 or (self._allow_fixed_csum and msgcrc == 0xFAFA):
                pac.isValid = True
            else:
                pac.isValid = False

        return pac

    def close(self):
        self._sockCommand.close()


class HwInterfaceFactory:

    def __init__(self):
        self._hw_interface = None

    def create_interface(self, select, **kwargs):
        # Close an interface before creating new one
        if self._hw_interface is not None:
            self._hw_interface.close()

        if select == 'serial':
            self._hw_interface = HwInterfaceSerial(**kwargs)
        elif select == 'zmq':
            self._hw_interface = HwInterfaceZMQ(**kwargs)
        else:
            print("HwInterfaceFactory: Selection not recognized")
            self._hw_interface = None

        return self._hw_interface

    @property
    def hw_interface(self):
        return self._hw_interface
