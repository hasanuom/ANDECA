"""Simple in‑process "sensor" that responds to a few commands.

This helper is useful when you don't have the real hardware attached.  It
creates a pair of connected pseudo‑terminals using the ``loop://`` handler in
pyserial; the test script (or any other client) can open the returned URL and
talk to the fake sensor.

Run this module in one terminal and ``sensor_test.py`` in another (pass the
loop URL printed by this script as the port argument).  The fake sensor will
respond with canned data for the firmware version, settings and a small set of
float samples for the time‑domain and spectrum packets.
"""

import threading
import time
import struct
import serial
from packet import Packet
import pac_ids as ids


def start_mock():
    # loop:// gives us a virtual cable – opening it twice yields two ends
    port = "loop://"  # pyserial built‑in virtual port
    ser = serial.serial_for_url(port, baudrate=1000000, timeout=0.1)
    print("mock sensor listening on", port)

    def run():
        while True:
            hdr = ser.read(4)
            if len(hdr) < 4:
                continue
            # read rest of packet header (8 bytes)
            rest = ser.read(8)
            if len(rest) < 8:
                continue
            # get payload length
            _, _, _, nbytes = struct.unpack(">HHHH", rest)
            payload = ser.read(nbytes)
            chk = ser.read(2)
            try:
                pkt = Packet.from_bytes(hdr + rest + payload + chk)
            except Exception:
                continue
            # choose a response
            if pkt.command & ids.GET_MASK == ids.PAC_ID_FW_VERS:
                resp_payload = b"MockSensor v0.1\n"
                cmd = ids.PAC_ID_FW_VERS | ids.GET_MASK
            elif pkt.command & ids.GET_MASK == ids.PAC_ID_TIME_DOMAIN_RX:
                samples = [i * 0.1 for i in range(16)]
                resp_payload = b"".join(struct.pack(">f", f) for f in samples)
                cmd = ids.PAC_ID_TIME_DOMAIN_RX | ids.GET_MASK
            elif pkt.command & ids.GET_MASK == ids.PAC_ID_SPECTRUM_RX:
                samples = [1.0 / (i + 1) for i in range(16)]
                resp_payload = b"".join(struct.pack(">f", f) for f in samples)
                cmd = ids.PAC_ID_SPECTRUM_RX | ids.GET_MASK
            elif pkt.command & ids.GET_MASK == ids.PAC_ID_SETTINGS:
                # return three 16-bit words as in the C code example
                resp_payload = struct.pack(">HHHf", 1, 4, 0, 0.75)
                cmd = ids.PAC_ID_SETTINGS | ids.GET_MASK
            else:
                # ignore others
                continue

            resp = Packet(device_address=pkt.device_address,
                          command=cmd,
                          seq_num=pkt.seq_num,
                          payload=resp_payload)
            ser.write(resp.to_bytes())
            time.sleep(0.01)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return port


if __name__ == "__main__":
    print("starting mock sensor; press Ctrl‑C to quit")
    try:
        port = start_mock()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("stopped")
