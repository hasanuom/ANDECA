#!/usr/bin/env python3
"""Connect to a drone via MAVLink and print LOCAL_POSITION_NED x/y/z.

This script follows the same connection style used in ndt_heatmap.py and
drone_connection.py, but intentionally does not include any NDT logic.
"""

import sys
import time
from pymavlink import mavutil


# Real Pixhawk over UART (Raspberry Pi): '/dev/ttyAMA0'
# USB serial Pixhawk: '/dev/ttyACM0'
# Simulator (sim_drone.py): 'udpin:0.0.0.0:14550'
MAVLINK_CONNECTION = '/dev/ttyAMA0'
MAVLINK_BAUD = 57600
POSITION_RATE_HZ = 10


def main() -> None:
	print(f"Connecting to MAVLink at '{MAVLINK_CONNECTION}' ...")
	try:
		master = mavutil.mavlink_connection(MAVLINK_CONNECTION, baud=MAVLINK_BAUD)
		master.wait_heartbeat(timeout=30)
	except Exception as exc:
		print(f"ERROR: MAVLink connection failed: {exc}", file=sys.stderr)
		sys.exit(1)

	print(f"Heartbeat received from system {master.target_system}.")

	# Ask ArduPilot/PX4 to stream position messages.
	master.mav.request_data_stream_send(
		master.target_system,
		master.target_component,
		mavutil.mavlink.MAV_DATA_STREAM_POSITION,
		POSITION_RATE_HZ,
		1,
	)

	print("Printing LOCAL_POSITION_NED (x, y, z) in meters. Press Ctrl+C to stop.")

	try:
		while True:
			msg = master.recv_match(type='LOCAL_POSITION_NED', blocking=True, timeout=1)
			if msg is None:
				continue

			print(f"x={msg.x: .3f} m, y={msg.y: .3f} m, z={msg.z: .3f} m")
			time.sleep(0.01)
	except KeyboardInterrupt:
		print("\nStopped by user.")


if __name__ == '__main__':
	main()
