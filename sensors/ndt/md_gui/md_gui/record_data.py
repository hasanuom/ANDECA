import os
import time
import queue
import struct
import md_packet

class RecordData():

    SYSTEM = 0x0D060CA7
    LOGFILE_MARKER = bytes('LOGENTRY', 'ascii')

    def __init__(self, message_queue: queue.Queue):
        self._message_queue = message_queue
        self._running = False
        self._mark = False

        # cwd = os.path.dirname(os.path.realpath(__file__))
        home_dir = os.path.expanduser("~")
        print(home_dir)
        self._filepath_base = os.path.join(home_dir, "logfile")
        if not os.path.exists(self._filepath_base):
            os.makedirs(self._filepath_base)
        self._suffix = ".log"
        self._fhandle = None

    def start(self):

        timestr = time.strftime("%Y%m%d-%H%M%S")
        filename = timestr + "_messages" + self._suffix
        filepath = os.path.join(self._filepath_base, filename)
        self._fhandle = open(filepath, "wb")
        if self._fhandle:
            self._running = True
            #self._fhandle.write(self._initial_file_marker)

    def stop(self):
        self._running = False

        if self._fhandle:
            self._fhandle.close()

    def mark(self):
        self._mark = True

    def _insert_mark_packet(self):

        # Convert nano to microseconds and 64-bit integer
        ts_us = int(time.time_ns() // 1000)
        print(ts_us)
        ts_bytes = struct.pack('<Q', ts_us)
        ts_bytes_alt = struct.pack('!Q', ts_us)

        header = int.to_bytes(0x0D060CA7, 4, byteorder='big')
        mark_pac = md_packet.MdPacket(address=0, command=0x3000, seq_num=0, payload=bytearray(ts_bytes), header=header)
        #format_str = '>IHHHHdH'
        #temp = struct.pack(format_str, self.SYSTEM, addr, cmd, seq, length, ts_us, crc)
        # print(struct.calcsize(format_str))

        self._fhandle.write(self.LOGFILE_MARKER + ts_bytes_alt)
        self._fhandle.write(mark_pac.generate_packet())


    def update(self):
        if self._mark == True:
            self._mark = False
            if self._running == True:
                self._insert_mark_packet()

        while not self._message_queue.empty():
            msg = self._message_queue.get()

            if self._running == True:
                #msg_bytes = array.array('B', msg).tostring()
                #print(msg_bytes)
                self._fhandle.write(self.LOGFILE_MARKER)
                self._fhandle.write(bytes(bytearray(msg)))



