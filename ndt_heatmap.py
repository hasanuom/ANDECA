#!/usr/bin/env python3
"""NDT Heatmap Mapper
====================
Connects to a Pixhawk 6C via MAVLink to retrieve drone XY position
(LOCAL_POSITION_NED) and simultaneously reads harmonic magnitude from the NDT
sensor over serial. Readings are recorded to a CSV file for CAPTURE_DURATION
seconds, then a 2D heatmap of magnitude vs XY position is plotted and saved.

Usage (real hardware):
    python3 ndt_heatmap.py

Usage (with simulator):
    Set MAVLINK_CONNECTION = 'udpin:0.0.0.0:14550' below,
    then start sim_drone.py first, then run this script.
"""

import sys
import os
import csv
import math
import time
import struct
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt
from pymavlink import mavutil

# Add NDT sensor module to path (files use flat relative imports)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sensors', 'ndt'))
from packet import PacketSerial, Packet                          # noqa: E402
from pac_ids import (GET_MASK, SET_MASK,                         # noqa: E402
                     PAC_ID_HARMONICS_RX, PAC_ID_SETTINGS_STREAMING)


# ============================================================
# CONFIGURATION — edit these constants before running
# ============================================================

# Total capture duration in seconds
CAPTURE_DURATION = 30.0

# MAVLink connection string:
#   Real Pixhawk over UART : '/dev/ttyAMA0'
#   Simulator (sim_drone.py): 'udpin:0.0.0.0:14550'
MAVLINK_CONNECTION = 'udpin:0.0.0.0:14550'
MAVLINK_BAUD = 57600          # only relevant for serial connections

# NDT sensor serial port and baud rate
NDT_PORT = '/dev/ttyUSB0'
NDT_BAUD = 1000000

# Harmonic index to record (0-based; harmonic 2 is the third harmonic)
HARMONIC_IDX = 2

# Output CSV file path (None = auto-timestamped in readings/)
OUTPUT_CSV = None

# Output directory for generated CSV and PNG files
OUTPUT_DIR = 'readings'

# Heatmap grid resolution (cells per axis for the binned average image)
HEATMAP_RESOLUTION = 50

# Show an interactive plot window after saving PNG.
# Set to False for headless/SSH runs so the script exits immediately.
SHOW_INTERACTIVE_PLOT = False

# ============================================================


def _parse_harmonics(data: bytes) -> list:
    """Convert a raw NDT harmonics payload into a list of dicts with
    keys 'real', 'imag', 'mag'.  Mirrors the TI DSP middle-endian float
    format used by the firmware."""
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
        harmonics.append({
            'real': real,
            'imag': imag,
            'mag': math.sqrt(real * real + imag * imag),
        })
    return harmonics


def _enable_streaming(ps: PacketSerial) -> None:
    """Send the streaming-enable command to the NDT sensor."""
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
    """Send the streaming-disable command and close the port."""
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
    """Bin all (x, y, magnitude) readings into a 2-D grid and render as a
    heatmap.  Cells with no readings are shown as white.  The figure is
    saved as a PNG alongside the CSV and displayed interactively."""
    xs_arr = np.array(xs)
    ys_arr = np.array(ys)
    mags_arr = np.array(mags)

    x_min, x_max = xs_arr.min(), xs_arr.max()
    y_min, y_max = ys_arr.min(), ys_arr.max()

    # Guard against zero range (drone didn't move on that axis)
    if x_max == x_min:
        x_min -= 0.5
        x_max += 0.5
    if y_max == y_min:
        y_min -= 0.5
        y_max += 0.5

    res = HEATMAP_RESOLUTION
    grid_sum = np.zeros((res, res))
    grid_cnt = np.zeros((res, res))

    xi = np.clip(
        ((xs_arr - x_min) / (x_max - x_min) * (res - 1)).astype(int), 0, res - 1
    )
    yi = np.clip(
        ((ys_arr - y_min) / (y_max - y_min) * (res - 1)).astype(int), 0, res - 1
    )
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

    # Overlay raw sample positions so coverage is visible
    ax.scatter(xs_arr, ys_arr, s=2, c='cyan', alpha=0.25, label='Sample positions')

    ax.set_xlabel('X  /  North (m)')
    ax.set_ylabel('Y  /  East (m)')
    ax.set_title(
        f'NDT Magnitude Heatmap — harmonic {HARMONIC_IDX}, '
        f'{len(xs)} samples, {CAPTURE_DURATION:.0f} s capture'
    )
    ax.legend(fontsize=8, loc='upper right')

    png_path = os.path.splitext(csv_path)[0] + '.png'
    fig.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f"Heatmap image saved to {png_path}")

    if SHOW_INTERACTIVE_PLOT:
        plt.show()
    else:
        plt.close(fig)


def main() -> None:
    # ── Resolve output CSV path ──────────────────────────────────────────────
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if OUTPUT_CSV is None:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = os.path.join(OUTPUT_DIR, f'ndt_heatmap_{ts}.csv')
    else:
        csv_path = os.path.join(OUTPUT_DIR, OUTPUT_CSV)

    # ── Connect to MAVLink ───────────────────────────────────────────────────
    print(f"Connecting to MAVLink at '{MAVLINK_CONNECTION}' ...")
    try:
        master = mavutil.mavlink_connection(MAVLINK_CONNECTION, baud=MAVLINK_BAUD)
        master.wait_heartbeat(timeout=30)
    except Exception as exc:
        print(f"ERROR: MAVLink connection failed: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Heartbeat received from system {master.target_system}.")

    # Request LOCAL_POSITION_NED at 10 Hz
    master.mav.request_data_stream_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_POSITION,
        10,   # rate Hz
        1,    # start
    )

    # ── Connect to NDT sensor ────────────────────────────────────────────────
    print(f"Connecting to NDT sensor on '{NDT_PORT}' ...")
    try:
        ps = PacketSerial(NDT_PORT, NDT_BAUD, timeout=0.1)
    except Exception as exc:
        print(f"ERROR: Cannot open NDT sensor on '{NDT_PORT}': {exc}", file=sys.stderr)
        sys.exit(1)
    _enable_streaming(ps)
    print("NDT streaming enabled.")

    # ── Capture loop ─────────────────────────────────────────────────────────
    print(
        f"\nCapturing for {CAPTURE_DURATION:.0f} s — press Ctrl+C to stop early.\n"
        f"Output CSV: {csv_path}\n"
    )

    records = []
    latest_x = None
    latest_y = None
    start = time.time()
    ndt_packet_count = 0
    position_msg_count = 0
    harmonic_packet_count = 0
    interrupted = False

    try:
        with open(csv_path, 'w', newline='') as fh:
            writer = csv.writer(fh)
            writer.writerow(['timestamp', 'x_m', 'y_m', f'magnitude_h{HARMONIC_IDX}'])

            while time.time() - start < CAPTURE_DURATION:
                # Drive the loop from the NDT serial receive (matches working scripts).
                # Keep the timeout short so MAVLink position messages are serviced often.
                pkt = ps.receive()

                # Drain ALL queued MAVLink position messages (non-blocking) so we
                # always have the latest position without blocking the NDT loop.
                while True:
                    pos = master.recv_match(
                        type='LOCAL_POSITION_NED', blocking=False
                    )
                    if pos is None:
                        break
                    latest_x = pos.x
                    latest_y = pos.y
                    position_msg_count += 1

                # Skip if NDT didn't return a complete packet this iteration
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

                mag = harmonics[HARMONIC_IDX]['mag']

                if latest_x is None:
                    # No position fix yet — skip but keep reading
                    continue

                ts_str = datetime.now().isoformat()
                writer.writerow(
                    [ts_str, f'{latest_x:.4f}', f'{latest_y:.4f}', f'{mag:.6f}']
                )
                records.append((latest_x, latest_y, mag))

                elapsed = time.time() - start
                print(
                    f"\r[{elapsed:6.1f} / {CAPTURE_DURATION:.0f} s]  "
                    f"x={latest_x:7.2f} m  y={latest_y:7.2f} m  "
                    f"mag={mag:.4f}  samples={len(records)}",
                    end='', flush=True,
                )

    except KeyboardInterrupt:
        interrupted = True
        print("\nCapture stopped early by user.")
    finally:
        _disable_streaming(ps)

    if interrupted:
        print(f"Partial capture saved to {csv_path}")
        return

    print(f"\n\nCapture complete. {len(records)} samples written to {csv_path}")

    if len(records) < 4:
        print(
            "Diagnostics: "
            f"position_msgs={position_msg_count}, "
            f"ndt_packets={ndt_packet_count}, "
            f"harmonic_packets={harmonic_packet_count}"
        )
        print("Not enough data to generate a heatmap (< 4 samples).")
        return

    xs, ys, mags = zip(*records)
    _plot_heatmap(list(xs), list(ys), list(mags), csv_path)


if __name__ == '__main__':
    main()
