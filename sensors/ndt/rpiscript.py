import serial
import struct
import time

# =================================================================
# HARDWARE CONSTANTS - FROM pac_settings.c & pac_info.c
# =================================================================
# From pac_settings.c: UART configuration
# Assuming standard high-speed for this sensor; verify with your specific file
BAUD_RATE = 115200 
SERIAL_PORT = '/dev/ttyUSB0'

# From packet.c: static uint16_t pac_header[] = {0xDE, 0x7E, 0xC7, 0xED}
# Big Endian representation of the 4 uint16 values (8 bytes total)
PAC_HEADER = b'\x00\xDE\x00\x7E\x00\xC7\x00\xED' 

# From pac_info.c: Command IDs (Example mapping - verify with your file)
CMD_GET_INFO    = 0x0001 
CMD_SET_SETTINGS = 0x0002
CMD_GET_DATA    = 0x0003

class SensorPacket:
    def __init__(self, raw_meta=None, payload=b''):
        self.address = 0
        self.command = 0
        self.seq_num = 0
        self.nbytes = 0
        self.payload = payload
        
        if raw_meta:
            # Unpacks the 8 bytes of metadata per md_packet_format.xlsx
            # Format: > (Big Endian) H (uint16_t)
            self.address, self.command, self.seq_num, self.nbytes = struct.unpack('>HHHH', raw_meta)

    @staticmethod
    def calculate_checksum(data: bytes) -> int:
        """
        Ported from pac_tx.c: pac_checksum_calculate
        A 16-bit summation of all bytes in the packet.
        """
        return sum(data) & 0xFFFF

def handle_packet(packet):
    """
    Ported logic from the switch statement in pac_handler.c
    """
    if packet.command == CMD_GET_DATA:
        # Assuming payload contains raw sensor values (e.g., 32-bit floats)
        # Porting the specific handling logic from pac_handler.c
        try:
            # Example: Unpacking a single 32-bit float from the start of the payload
            value = struct.unpack('>f', packet.payload[:4])[0]
            print(f"[DATA] Seq: {packet.seq_num} | Value: {value:.4f}")
        except struct.error:
            print(f"[DATA] Raw Payload (Hex): {packet.payload.hex()}")

    elif packet.command == CMD_GET_INFO:
        print(f"[INFO] Sensor info received from Addr: {packet.address}")

    else:
        print(f"[UNK] Cmd: {packet.command} | Seq: {packet.seq_num} | Payload: {len(packet.payload)} bytes")

def main():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        print(f"--- Port {SERIAL_PORT} Opened at {BAUD_RATE} ---")
    except Exception as e:
        print(f"FAILED to open serial port: {e}")
        return

    while True:
        # STEP 1: Syncing to 8-byte Header (from packet.c)
        if ser.read(1) == b'\x00':
            if ser.read(1) == b'\xde':
                # Match the rest of the uint16 array {0xDE, 0x7E, 0xC7, 0xED}
                if ser.read(6) == b'\x00\x7e\x00\xc7\x00\xed':
                    
                    # STEP 2: Read Metadata (8 bytes)
                    raw_meta = ser.read(8)
                    if len(raw_meta) < 8: continue
                    
                    # Extract nbytes to know how much payload follows
                    _, _, _, nbytes = struct.unpack('>HHHH', raw_meta)
                    
                    # STEP 3: Read Payload
                    payload = ser.read(nbytes)
                    
                    # STEP 4: Read Checksum (2 bytes)
                    raw_chk = ser.read(2)
                    if len(raw_chk) < 2: continue
                    received_chk = struct.unpack('>H', raw_chk)[0]

                    # STEP 5: Integrity Check (as per pac_tx.c)
                    full_data_for_chk = PAC_HEADER + raw_meta + payload
                    if SensorPacket.calculate_checksum(full_data_for_chk) == received_chk:
                        pkt = SensorPacket(raw_meta, payload)
                        handle_packet(pkt)
                    else:
                        print("!! Checksum Mismatch !!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopping...")