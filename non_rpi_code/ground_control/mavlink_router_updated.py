#!/usr/bin/env python3
"""
mavlink_router.py

Routes MAVLink from a serial port to two UDP outputs simultaneously.
- UDP 14550 -> Mission Planner
- UDP 14551 -> inbound from vicon client script

Usage:
    py mavlink_router.py

Stop with Ctrl+C.
"""

import threading
from pymavlink import mavutil

SERIAL_PORT = "\\\\.\\COM9"
BAUD_RATE = 57600
UDP_OUT_1 = "udpout:127.0.0.1:14550"  # Mission Planner
UDP_IN_VICON = "udpin:127.0.0.1:14551"  # Vicon script sends here


def forward_serial_to_udp(serial_conn, udp1):
    """Forward messages from serial port to Mission Planner UDP output."""
    while True:
        try:
            msg = serial_conn.recv_match(blocking=True, timeout=0.1)
            if msg is None:
                continue
            buf = msg.get_msgbuf()
            try:
                udp1.write(buf)
            except Exception:
                pass
        except Exception:
            pass


def forward_udp_to_serial(udp_conn, serial_conn, mirror_udp_conn=None):
    """Forward messages from UDP input back to serial port, with optional UDP mirror."""
    while True:
        try:
            msg = udp_conn.recv_match(blocking=True, timeout=0.1)
            if msg is None:
                continue
            buf = msg.get_msgbuf()
            try:
                serial_conn.write(buf)
            except Exception:
                pass
            if mirror_udp_conn is not None:
                try:
                    mirror_udp_conn.write(buf)
                except Exception:
                    pass
        except Exception:
            pass


def main():
    print(f"Opening serial {SERIAL_PORT} at {BAUD_RATE} baud...")
    master = mavutil.mavlink_connection(SERIAL_PORT, baud=BAUD_RATE)

    print(f"Opening UDP output to {UDP_OUT_1}...")
    out1 = mavutil.mavlink_connection(UDP_OUT_1)

    print(f"Opening UDP input on {UDP_IN_VICON}...")
    in_vicon = mavutil.mavlink_connection(UDP_IN_VICON)

    print("Routing MAVLink traffic bidirectionally. Press Ctrl+C to stop.")
    print("  Connect Mission Planner to UDP port 14550")
    print("  Vicon script sends to UDP port 14551")

    # Start forwarding threads
    t1 = threading.Thread(target=forward_serial_to_udp, args=(master, out1), daemon=True)
    t2 = threading.Thread(target=forward_udp_to_serial, args=(out1, master), daemon=True)
    t3 = threading.Thread(target=forward_udp_to_serial, args=(in_vicon, master, out1), daemon=True)

    t1.start()
    t2.start()
    t3.start()

    try:
        t1.join()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
