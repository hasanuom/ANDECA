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


def request_local_position_ned(master) -> None:
	"""Request LOCAL_POSITION_NED using both legacy and modern MAVLink APIs."""
	# Legacy stream request (works on many firmwares)
	master.mav.request_data_stream_send(
		master.target_system,
		master.target_component,
		mavutil.mavlink.MAV_DATA_STREAM_POSITION,
		POSITION_RATE_HZ,
		1,
	)

	# Direct message interval request for LOCAL_POSITION_NED (msg id 32)
	interval_us = int(1_000_000 / POSITION_RATE_HZ)
	master.mav.command_long_send(
		master.target_system,
		master.target_component,
		mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
		0,
		mavutil.mavlink.MAVLINK_MSG_ID_LOCAL_POSITION_NED,
		interval_us,
		0,
		0,
		0,
		0,
		0,
	)


def main() -> None:
	print(f"Connecting to MAVLink at '{MAVLINK_CONNECTION}' ...")
	try:
		master = mavutil.mavlink_connection(MAVLINK_CONNECTION, baud=MAVLINK_BAUD)
		master.wait_heartbeat(timeout=30)
	except Exception as exc:
		print(f"ERROR: MAVLink connection failed: {exc}", file=sys.stderr)
		sys.exit(1)

	print(f"Heartbeat received from system {master.target_system}.")

	request_local_position_ned(master)

	print("Printing LOCAL_POSITION_NED (x, y, z) in meters. Press Ctrl+C to stop.")
	print("If nothing prints, EKF likely has no valid local position yet.")

	last_diag = time.time()

	try:
		while True:
			msg = master.recv_match(type='LOCAL_POSITION_NED', blocking=True, timeout=1)
			if msg is None:
				now = time.time()
				if now - last_diag >= 3.0:
					print(
						"Waiting for LOCAL_POSITION_NED... "
						"Check EKF status, GPS/vision availability, and that the vehicle is initialized."
					)
					last_diag = now
				continue

			print(f"x={msg.x: .3f} m, y={msg.y: .3f} m, z={msg.z: .3f} m")
			time.sleep(0.01)
	except KeyboardInterrupt:
		print("\nStopped by user.")


if __name__ == '__main__':
	main()
