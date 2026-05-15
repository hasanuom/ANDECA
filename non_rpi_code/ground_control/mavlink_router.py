#!/usr/bin/env python3
"""
mavlink_router.py

Routes MAVLink from a serial port to two UDP outputs simultaneously.
- UDP 14550 -> Mission Planner
- UDP 14551 -> vicon client script

Usage:
    py mavlink_router.py

Stop with Ctrl+C.
"""

import threading
from pymavlink import mavutil

SERIAL_PORT = "\\\\.\\COM9"
BAUD_RATE = 57600
UDP_OUT_1 = "udpout:127.0.0.1:14550"  # Mission Planner
UDP_OUT_2 = "udpout:127.0.0.1:14551"  # Vicon script


def forward_serial_to_udp(serial_conn, udp1, udp2):
    """Forward messages from serial port to both UDP outputs."""
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
            try:
                udp2.write(buf)
            except Exception:
                pass
        except Exception:
            pass


def forward_udp_to_serial(udp_conn, serial_conn):
    """Forward messages from UDP input back to serial port."""
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
        except Exception:
            pass


def main():
    print(f"Opening serial {SERIAL_PORT} at {BAUD_RATE} baud...")
    master = mavutil.mavlink_connection(SERIAL_PORT, baud=BAUD_RATE)

    print(f"Opening UDP output to {UDP_OUT_1}...")
    out1 = mavutil.mavlink_connection(UDP_OUT_1)

    print(f"Opening UDP output to {UDP_OUT_2}...")
    out2 = mavutil.mavlink_connection(UDP_OUT_2)

    print("Routing MAVLink traffic bidirectionally. Press Ctrl+C to stop.")
    print("  Connect Mission Planner to UDP port 14550")
    print("  Vicon script connects to UDP port 14551")

    # Start forwarding threads
    t1 = threading.Thread(target=forward_serial_to_udp, args=(master, out1, out2), daemon=True)
    t2 = threading.Thread(target=forward_udp_to_serial, args=(out1, master), daemon=True)
    t3 = threading.Thread(target=forward_udp_to_serial, args=(out2, master), daemon=True)

    t1.start()
    t2.start()
    t3.start()

    try:
        t1.join()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()