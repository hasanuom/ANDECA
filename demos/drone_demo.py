#!/usr/bin/env python3
"""Drone demo: LOCAL_POSITION_NED XY + NDT magnitude + laser distance.

This script combines:
- MAVLink drone position from LOCAL_POSITION_NED (reference: connect_and_print_drone_location.py)
- NDT harmonic magnitude capture (reference: ndt_heatmap.py)
- Laser distance capture (VL53L4CD)

Behavior:
- starts logging immediately when launched
- stop with Ctrl+C
- saves CSV and then saves/displays NDT heatmap using XY + magnitude only

The CSV includes laser distance, but laser is not used in the heatmap.
"""

from __future__ import annotations

import csv
import math
import os
import struct
import sys
import time
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
from pymavlink import mavutil

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

try:
    from sensors.ndt.packet import PacketSerial, Packet  # type: ignore
    from sensors.ndt.pac_ids import (  # type: ignore
        GET_MASK,
        SET_MASK,
        PAC_ID_HARMONICS_RX,
        PAC_ID_SETTINGS_STREAMING,
    )
except Exception:
    sys.path.insert(0, os.path.join(PROJECT_ROOT, 'sensors', 'ndt'))
    from packet import PacketSerial, Packet  # type: ignore
    from pac_ids import (  # type: ignore
        GET_MASK,
        SET_MASK,
        PAC_ID_HARMONICS_RX,
        PAC_ID_SETTINGS_STREAMING,
    )


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

# NDT sensor serial port and baud rate
NDT_PORT = '/dev/ttyUSB0'
NDT_BAUD = 1000000
HARMONIC_IDX = 2

OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'readings')
OUTPUT_CSV = None
HEATMAP_RESOLUTION = 50
SHOW_INTERACTIVE_PLOT = True


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


def _parse_harmonics(data: bytes) -> list:
    n_floats = len(data) // 4
    bigendian = bytearray()
    for i in range(0, len(data), 4):
        lsword = data[i:i + 2]
        word = data[i + 2:i + 4] + lsword
        bigendian += word
    floats = list(struct.unpack(f">{n_floats}f", bytes(bigendian)))
    harmonics = []
    for i in range(0, len(floats), 2):
        real = floats[i]
        imag = floats[i + 1] if i + 1 < len(floats) else 0.0
        harmonics.append(
            {
                'real': real,
                'imag': imag,
                'mag': math.sqrt(real * real + imag * imag),
            }
        )
    return harmonics


def _enable_streaming(ps: PacketSerial) -> None:
    payload = struct.pack(">B", 4)
    req = Packet(
        device_address=0,
        command=SET_MASK | PAC_ID_SETTINGS_STREAMING,
        seq_num=0,
        payload=payload,
    )
    ps.send(req)
    time.sleep(0.2)


def _disable_streaming(ps: PacketSerial) -> None:
    try:
        off = struct.pack(">B", 0)
        req = Packet(
            device_address=0,
            command=SET_MASK | PAC_ID_SETTINGS_STREAMING,
            seq_num=0,
            payload=off,
        )
        ps.send(req)
    except Exception:
        pass
    try:
        ps.ser.close()
    except Exception:
        pass


def _plot_heatmap(xs: list, ys: list, mags: list, csv_path: str) -> None:
    xs_arr = np.array(xs)
    ys_arr = np.array(ys)
    mags_arr = np.array(mags)

    x_min, x_max = xs_arr.min(), xs_arr.max()
    y_min, y_max = ys_arr.min(), ys_arr.max()

    if x_max == x_min:
        x_min -= 0.5
        x_max += 0.5
    if y_max == y_min:
        y_min -= 0.5
        y_max += 0.5

    res = HEATMAP_RESOLUTION
    grid_sum = np.zeros((res, res))
    grid_cnt = np.zeros((res, res))

    xi = np.clip(((xs_arr - x_min) / (x_max - x_min) * (res - 1)).astype(int), 0, res - 1)
    yi = np.clip(((ys_arr - y_min) / (y_max - y_min) * (res - 1)).astype(int), 0, res - 1)
    np.add.at(grid_sum, (yi, xi), mags_arr)
    np.add.at(grid_cnt, (yi, xi), 1)

    grid_avg = np.full((res, res), np.nan)
    mask = grid_cnt > 0
    grid_avg[mask] = grid_sum[mask] / grid_cnt[mask]

    fig, ax = plt.subplots(figsize=(10, 8))
    cmap = plt.get_cmap('hot').copy()
    cmap.set_bad(color='white')

    im = ax.imshow(
        grid_avg,
        origin='lower',
        extent=[x_min, x_max, y_min, y_max],
        aspect='auto',
        cmap=cmap,
        interpolation='nearest',
    )
    plt.colorbar(im, ax=ax, label=f'NDT Magnitude (harmonic {HARMONIC_IDX})')
    ax.scatter(xs_arr, ys_arr, s=2, c='cyan', alpha=0.25, label='Sample positions')

    ax.set_xlabel('X / North (m)')
    ax.set_ylabel('Y / East (m)')
    ax.set_title(f'Drone NDT Heatmap (LOCAL_POSITION_NED XY), {len(xs)} samples')
    ax.legend(fontsize=8, loc='upper right')

    png_path = os.path.splitext(csv_path)[0] + '.png'
    fig.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f"Heatmap image saved to {png_path}")

    if SHOW_INTERACTIVE_PLOT:
        plt.show()
    else:
        plt.close(fig)


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


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if OUTPUT_CSV is None:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = os.path.join(OUTPUT_DIR, f'drone_ndt_heatmap_{ts}.csv')
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

    print(f"Connecting to NDT sensor on '{NDT_PORT}' ...")
    try:
        ps = PacketSerial(NDT_PORT, NDT_BAUD, timeout=0.1)
    except Exception as exc:
        print(f"ERROR: cannot open NDT sensor on '{NDT_PORT}': {exc}")
        sys.exit(1)
    _enable_streaming(ps)
    print("NDT streaming enabled.")

    vl53 = _init_laser_sensor()

    print(
        "\nLogging started. Press Ctrl+C to stop and generate heatmap.\n"
        f"Output CSV: {csv_path}\n"
    )

    latest_x = None
    latest_y = None
    latest_laser_cm = None
    records = []

    ndt_packet_count = 0
    position_msg_count = 0
    harmonic_packet_count = 0
    last_diag = time.time()

    try:
        with open(csv_path, 'w', newline='') as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    'timestamp',
                    'x_m',
                    'y_m',
                    f'magnitude_h{HARMONIC_IDX}',
                    'laser_distance_cm',
                ]
            )

            while True:
                while True:
                    pos = master.recv_match(type='LOCAL_POSITION_NED', blocking=False)
                    if pos is None:
                        break
                    latest_x = float(pos.x)
                    latest_y = float(pos.y)
                    position_msg_count += 1

                if latest_x is None and (time.time() - last_diag) >= 3.0:
                    print(
                        "Waiting for LOCAL_POSITION_NED... "
                        "EKF local position is required for x/y logging."
                    )
                    last_diag = time.time()

                if vl53 is not None:
                    try:
                        if vl53.data_ready:
                            latest_laser_cm = float(vl53.distance)
                            vl53.clear_interrupt()
                    except Exception:
                        pass

                pkt = ps.receive()
                if pkt is None:
                    continue

                ndt_packet_count += 1
                if (pkt.command & ~GET_MASK) != PAC_ID_HARMONICS_RX:
                    continue
                harmonic_packet_count += 1

                try:
                    harmonics = _parse_harmonics(pkt.payload)
                except Exception:
                    continue

                if HARMONIC_IDX >= len(harmonics):
                    continue

                if latest_x is None or latest_y is None:
                    continue

                mag = harmonics[HARMONIC_IDX]['mag']
                ts_str = datetime.now().isoformat()
                laser_text = '' if latest_laser_cm is None else f'{latest_laser_cm:.3f}'

                writer.writerow(
                    [
                        ts_str,
                        f'{latest_x:.4f}',
                        f'{latest_y:.4f}',
                        f'{mag:.6f}',
                        laser_text,
                    ]
                )

                records.append((latest_x, latest_y, mag))
                print(
                    f"\rx={latest_x:7.3f} m  y={latest_y:7.3f} m  "
                    f"mag={mag:9.4f}  laser_cm={laser_text or 'n/a':>7}  "
                    f"samples={len(records)}",
                    end='',
                    flush=True,
                )

    except KeyboardInterrupt:
        print("\nCapture stopped by user.")
    finally:
        _disable_streaming(ps)

    print(
        f"\nCapture complete. {len(records)} samples written to {csv_path} "
        f"(position_msgs={position_msg_count}, "
        f"NDT packets={ndt_packet_count}, harmonic packets={harmonic_packet_count})."
    )

    if len(records) < 4:
        print("Not enough data to generate heatmap (< 4 samples).")
        return

    xs, ys, mags = zip(*records)
    _plot_heatmap(list(xs), list(ys), list(mags), csv_path)


if __name__ == '__main__':
    main()
