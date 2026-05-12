#!/usr/bin/env python3
"""Drone-vicon style demo using LOCAL_POSITION_NED from MAVLink.

This script mirrors the Vicon-only workflow from vicon_only.py, but uses the
working LOCAL_POSITION_NED approach from drone_demo.py for position data.

Behavior:
- starts logging immediately when launched
- stop with Ctrl+C
- writes a timestamped CSV with x/y and optional laser distance
- saves and displays an XY-plane PNG

The laser sensor is optional; if it is not present, the script keeps running
and leaves the laser column blank.
"""

from __future__ import annotations

import csv
import os
import sys
import threading
import time
from datetime import datetime
from typing import Optional

import matplotlib.pyplot as plt
from pymavlink import mavutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------

# MAVLink connection:
#   Pixhawk on Pi UART: '/dev/ttyAMA0'
#   Pixhawk USB serial: '/dev/ttyACM0'
#   Simulator: 'udpin:0.0.0.0:14550'
MAVLINK_CONNECTION = '/dev/ttyAMA0'
MAVLINK_BAUD = 57600
POSITION_RATE_HZ = 10

OUTPUT_DIR = '/media/andeca/ENUODA/readings/drone_vicon'
OUTPUT_CSV = None
SHOW_INTERACTIVE_PLOT = True
PRINT_EVERY_N_SAMPLES = 10


def request_local_position_ned(master) -> None:
    """Request LOCAL_POSITION_NED using legacy stream and message interval."""
    master.mav.request_data_stream_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_POSITION,
        POSITION_RATE_HZ,
        1,
    )

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


def _init_laser_sensor():
    try:
        import board  # type: ignore
        import adafruit_vl53l4cd  # type: ignore

        i2c = board.I2C()
        vl53 = adafruit_vl53l4cd.VL53L4CD(i2c)
        vl53.inter_measurement = 0
        vl53.timing_budget = 50
        vl53.start_ranging()
        print("Laser sensor initialized.")
        return vl53
    except Exception as exc:
        print(f"Laser sensor init failed: {exc}; laser distance column will be blank.")
        return None


def _plot_xy_path(xs: list, ys: list, csv_path: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.plot(xs, ys, '-', linewidth=1.0, alpha=0.75, label='Path')
    ax.scatter(xs, ys, s=10, c='cyan', alpha=0.4, label='Samples')

    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_title(f'Drone XY Plane, {len(xs)} samples')
    ax.grid(True)
    ax.axis('equal')
    ax.legend(fontsize=8, loc='best')

    png_path = os.path.splitext(csv_path)[0] + '.png'
    fig.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f"XY image saved to {png_path}")

    if SHOW_INTERACTIVE_PLOT:
        plt.show()
    else:
        plt.close(fig)


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if OUTPUT_CSV is None:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = os.path.join(OUTPUT_DIR, f'drone_vicon_{ts}.csv')
    else:
        csv_path = os.path.join(OUTPUT_DIR, OUTPUT_CSV)

    print(f"Connecting to MAVLink at '{MAVLINK_CONNECTION}' ...")
    try:
        master = mavutil.mavlink_connection(MAVLINK_CONNECTION, baud=MAVLINK_BAUD)
        master.wait_heartbeat(timeout=30)
    except Exception as exc:
        print(f"ERROR: MAVLink connection failed: {exc}")
        sys.exit(1)
    print(f"Heartbeat received from system {master.target_system}.")

    request_local_position_ned(master)

    vl53 = _init_laser_sensor()

    print(
        "\nLogging started. Press Ctrl+C to stop and generate the XY plot.\n"
        f"Output CSV: {csv_path}\n"
    )

    latest_x = None
    latest_y = None
    latest_laser_cm = None
    rows = []
    sample_count = 0
    last_diag = time.time()

    try:
        with open(csv_path, 'w', newline='') as fh:
            writer = csv.writer(fh)
            writer.writerow(['timestamp', 'x_m', 'y_m', 'laser_distance_cm'])

            while True:
                while True:
                    pos = master.recv_match(type='LOCAL_POSITION_NED', blocking=False)
                    if pos is None:
                        break
                    latest_x = float(pos.x)
                    latest_y = float(pos.y)

                if vl53 is not None:
                    try:
                        if vl53.data_ready:
                            latest_laser_cm = float(vl53.distance)
                            vl53.clear_interrupt()
                    except Exception:
                        pass

                if latest_x is None or latest_y is None:
                    if (time.time() - last_diag) >= 3.0:
                        print("Waiting for LOCAL_POSITION_NED...")
                        last_diag = time.time()
                    time.sleep(0.01)
                    continue

                ts_str = datetime.now().isoformat()
                laser_text = '' if latest_laser_cm is None else f'{latest_laser_cm:.3f}'
                writer.writerow([ts_str, f'{latest_x:.4f}', f'{latest_y:.4f}', laser_text])
                rows.append((latest_x, latest_y, latest_laser_cm))
                sample_count += 1

                if sample_count == 1 or (sample_count % PRINT_EVERY_N_SAMPLES) == 0:
                    print(
                        f"\rx={latest_x:7.3f} m  y={latest_y:7.3f} m  "
                        f"laser_cm={laser_text or 'n/a':>7}  samples={sample_count}",
                        end='',
                        flush=True,
                    )

                time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nCapture stopped by user.")
    finally:
        try:
            master.close()
        except Exception:
            pass

    print(f"\nCapture complete. {len(rows)} samples written to {csv_path}.")

    if len(rows) < 2:
        print("Not enough data to generate XY plot.")
        return

    xs = [r[0] for r in rows]
    ys = [r[1] for r in rows]
    _plot_xy_path(xs, ys, csv_path)


if __name__ == '__main__':
    main()
