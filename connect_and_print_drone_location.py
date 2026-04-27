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

	# Also request common fallback messages so we can still show useful data
	# even when EKF local position is not available.
	for msg_id in (
		mavutil.mavlink.MAVLINK_MSG_ID_GLOBAL_POSITION_INT,
		mavutil.mavlink.MAVLINK_MSG_ID_AHRS2,
		mavutil.mavlink.MAVLINK_MSG_ID_VFR_HUD,
	):
		master.mav.command_long_send(
			master.target_system,
			master.target_component,
			mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
			0,
			msg_id,
			interval_us,
			0,
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

	print("Printing best-available x/y/z data in meters. Press Ctrl+C to stop.")
	print("Priority: LOCAL_POSITION_NED -> GLOBAL_POSITION_INT -> AHRS2/VFR_HUD altitude.")

	last_diag = time.time()
	last_line_time = 0.0

	latest = {
		'x': None,
		'y': None,
		'z': None,
		'source': None,
	}

	try:
		while True:
			msg = master.recv_match(
				type=['LOCAL_POSITION_NED', 'GLOBAL_POSITION_INT', 'AHRS2', 'VFR_HUD'],
				blocking=True,
				timeout=1,
			)
			if msg is None:
				now = time.time()
				if now - last_diag >= 3.0:
					print(
						"Waiting for telemetry... no LOCAL_POSITION_NED yet "
						"(expected without GPS/vision local-position source)."
					)
					last_diag = now
				continue

			mtype = msg.get_type()
			if mtype == 'LOCAL_POSITION_NED':
				latest['x'] = float(msg.x)
				latest['y'] = float(msg.y)
				latest['z'] = float(msg.z)
				latest['source'] = 'LOCAL_POSITION_NED'
			elif mtype == 'GLOBAL_POSITION_INT':
				# Convert from millimeters to meters for altitude fields.
				# Keep x/y as None because this is geodetic data (lat/lon), not local XY.
				latest['z'] = -float(msg.relative_alt) / 1000.0
				latest['source'] = 'GLOBAL_POSITION_INT(relative_alt)'
			elif mtype == 'AHRS2':
				latest['z'] = -float(msg.altitude)
				latest['source'] = 'AHRS2(altitude)'
			elif mtype == 'VFR_HUD':
				latest['z'] = -float(msg.alt)
				latest['source'] = 'VFR_HUD(alt)'

			now = time.time()
			if now - last_line_time < 0.1:
				continue
			last_line_time = now

			x_text = f"{latest['x']: .3f}" if latest['x'] is not None else '  n/a'
			y_text = f"{latest['y']: .3f}" if latest['y'] is not None else '  n/a'
			z_text = f"{latest['z']: .3f}" if latest['z'] is not None else '  n/a'
			src = latest['source'] or 'unknown'

			print(f"x={x_text} m, y={y_text} m, z={z_text} m  [{src}]")
	except KeyboardInterrupt:
		print("\nStopped by user.")


if __name__ == '__main__':
	main()
