"""Command‑line tool for talking to the metal‑detector sensor.

This script opens a serial port (default /dev/ttyUSB0 at 115200) and sends a
series of requests to the device.  Received packets are interpreted using the
logic in :mod:`pac_handlers` and printed as human‑readable summaries.

Usage::

    python3 sensor_test.py [port]

The port argument may be a real serial device or, for offline testing, a
pyserial "loop://" URL.
"""

import sys
import time
from packet import Packet, PacketSerial
import pac_ids as ids
from pac_handlers import parse_packet, summary


def send_and_print(link: PacketSerial, pkt: Packet) -> None:
    """Send *pkt* and print response (if any)."""
    print(f"--> send cmd=0x{pkt.command:04X} seq={pkt.seq_num}")
    link.send(pkt)
    # give the device a moment to reply
    time.sleep(0.05)
    resp = link.receive()
    if resp is None:
        print("<-- (no reply)")
        return
    print(f"<-- recv cmd=0x{resp.command:04X} seq={resp.seq_num} nbytes={len(resp.payload)}")
    payload = parse_packet(resp)
    print("    ", summary(payload))


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
    link = PacketSerial(port, baudrate=115200, timeout=0.2)
    print(f"opened {port}")

    seq = 1
    # request firmware version
    pkt = Packet(device_address=ids.DEFAULT_DEVICE_ADDRESS,
                 command=ids.PAC_ID_FW_VERS | ids.GET_MASK,
                 seq_num=seq)
    send_and_print(link, pkt)
    seq += 1

    # ask for one block of time-domain RX data
    pkt = Packet(device_address=ids.DEFAULT_DEVICE_ADDRESS,
                 command=ids.PAC_ID_TIME_DOMAIN_RX | ids.GET_MASK,
                 seq_num=seq)
    send_and_print(link, pkt)
    seq += 1

    # ask for spectrum RX
    pkt = Packet(device_address=ids.DEFAULT_DEVICE_ADDRESS,
                 command=ids.PAC_ID_SPECTRUM_RX | ids.GET_MASK,
                 seq_num=seq)
    send_and_print(link, pkt)
    seq += 1

    # ask for settings
    pkt = Packet(device_address=ids.DEFAULT_DEVICE_ADDRESS,
                 command=ids.PAC_ID_SETTINGS | ids.GET_MASK,
                 seq_num=seq)
    send_and_print(link, pkt)


if __name__ == "__main__":
    main()
