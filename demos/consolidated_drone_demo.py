#!/usr/bin/env python3
"""Consolidated no-drone demo: Vicon XY + NDT magnitude + laser distance.

This script is based on no_drone_demo.py, but writes all CSV data into a
single consolidated file instead of separate per-harmonic CSVs.

Capture behavior:
- starts logging immediately when launched
- stop with Ctrl+C
- saves one consolidated CSV, then saves/displays a heatmap of NDT magnitude
  vs Vicon XY
- also saves/displays the harmonics 0-3 figure

The consolidated CSV contains a capture section followed by h0-h3 sections.
"""

from __future__ import annotations

import csv
import math
import os
import struct
import sys
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import matplotlib.pyplot as plt
import numpy as np
import requests

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

API_BASE_URL = "http://192.168.10.1:8080"
BEARER_TOKEN = "changeme"
TRIAL_NAME = "Consolidated_NoDrone_NDT_Vicon"

NDT_PORT = '/dev/ttyUSB0'
NDT_BAUD = 1000000
HARMONIC_IDX = 2

VICON_POLL_INTERVAL_S = 0.05
INCLUDE_ROTATION = False
PRINT_EVERY_N_SAMPLES = 10

OUTPUT_DIR = '/media/andeca/ENUODA/readings/consolidated_no_drone_demo'
OUTPUT_CSV = None
HEATMAP_RESOLUTION = 50
SHOW_INTERACTIVE_PLOT = True


class ViconApiClient:
    def __init__(self, base_url: str, bearer_token: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json",
            }
        )

    def ping(self) -> Dict[str, Any]:
        r = self.session.get(f"{self.base_url}/v1/ping", timeout=2.0)
        r.raise_for_status()
        return r.json()

    def status(self) -> Dict[str, Any]:
        r = self.session.get(f"{self.base_url}/v1/status", timeout=2.0)
        r.raise_for_status()
        return r.json()

    def start(self, trial_name: str, duration: Optional[float] = None) -> Dict[str, Any]:
        payload = {
            "trial_name": trial_name,
            "duration": duration,
            "command_id": f"start-{uuid.uuid4()}",
        }
        r = self.session.post(f"{self.base_url}/v1/start", json=payload, timeout=3.0)
        r.raise_for_status()
        return r.json()

    def stop(self, reason: str = "") -> Dict[str, Any]:
        payload = {
            "reason": reason,
            "command_id": f"stop-{uuid.uuid4()}",
        }
        r = self.session.post(f"{self.base_url}/v1/stop", json=payload, timeout=3.0)
        r.raise_for_status()
        return r.json()

    def live_latest(self, include_rotation: bool = False) -> Dict[str, Any]:
        params = {"include_rotation": str(include_rotation).lower()}
        r = self.session.get(f"{self.base_url}/v1/live/latest", params=params, timeout=2.0)
        r.raise_for_status()
        return r.json()


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

    ax.set_xlabel('X (Vicon, m)')
    ax.set_ylabel('Y (Vicon, m)')
    ax.set_title(f'Consolidated No-Drone NDT Heatmap (Vicon XY), {len(xs)} samples')
    ax.legend(fontsize=8, loc='upper right')

    png_path = os.path.splitext(csv_path)[0] + '.png'
    fig.savefig(png_path, dpi=150, bbox_inches='tight')
    print(f"Heatmap image saved to {png_path}")

    if SHOW_INTERACTIVE_PLOT:
        plt.show()
    else:
        plt.close(fig)


def _plot_harmonics_figure(harmonic_plot_records: list, csv_path: str) -> None:
    if not harmonic_plot_records:
        print("No harmonic records available for harmonics figure.")
        return

    sample_idx = [r[0] for r in harmonic_plot_records]
    h0 = [r[1] for r in harmonic_plot_records]
    h1 = [r[2] for r in harmonic_plot_records]
    h2 = [r[3] for r in harmonic_plot_records]
    h3 = [r[4] for r in harmonic_plot_records]

    fig, axs = plt.subplots(2, 2, figsize=(12, 8))
    axs[0, 0].plot(sample_idx, h0, '-')
    axs[0, 0].set_title('Harmonic 0')
    axs[0, 0].set_xlabel('sample #')
    axs[0, 0].set_ylabel('magnitude')
    axs[0, 0].grid(True)

    axs[0, 1].plot(sample_idx, h1, '-')
    axs[0, 1].set_title('Harmonic 1')
    axs[0, 1].set_xlabel('sample #')
    axs[0, 1].set_ylabel('magnitude')
    axs[0, 1].grid(True)

    axs[1, 0].plot(sample_idx, h2, '-')
    axs[1, 0].set_title('Harmonic 2')
    axs[1, 0].set_xlabel('sample #')
    axs[1, 0].set_ylabel('magnitude')
    axs[1, 0].grid(True)

    axs[1, 1].plot(sample_idx, h3, '-')
    axs[1, 1].set_title('Harmonic 3')
    axs[1, 1].set_xlabel('sample #')
    axs[1, 1].set_ylabel('magnitude')
    axs[1, 1].grid(True)

    fig.suptitle('Harmonics 0-3 Magnitude vs Sample #')
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    fig_path = os.path.splitext(csv_path)[0] + '_harmonics.png'
    fig.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"Harmonics figure saved to {fig_path}")

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


def _vicon_poll_worker(
    client: ViconApiClient,
    include_rotation: bool,
    poll_interval_s: float,
    stop_event: threading.Event,
    latest_pose: Dict[str, Optional[float]],
    pose_lock: threading.Lock,
) -> None:
    while not stop_event.is_set():
        try:
            vicon_resp = client.live_latest(include_rotation=include_rotation)
            sample = vicon_resp.get('sample')
            if sample is not None:
                tx_mm = sample.get('tx_mm')
                ty_mm = sample.get('ty_mm')
                if tx_mm is not None and ty_mm is not None:
                    with pose_lock:
                        latest_pose['x'] = float(tx_mm) / 1000.0
                        latest_pose['y'] = float(ty_mm) / 1000.0
        except Exception:
            pass
        stop_event.wait(poll_interval_s)


def _write_consolidated_csv(
    csv_path: str,
    capture_rows: list,
    harmonic_rows: Dict[int, list],
) -> None:
    with open(csv_path, 'w', newline='') as fh:
        writer = csv.writer(fh)

        writer.writerow(['section', 'capture'])
        writer.writerow(['timestamp', 'x_m', 'y_m', f'magnitude_h{HARMONIC_IDX}', 'laser_distance_cm'])
        writer.writerows(capture_rows)

        for i in range(4):
            writer.writerow([])
            writer.writerow(['section', f'h{i}'])
            writer.writerow(['timestamp', 'pkt', 'real', 'imag', 'mag'])
            writer.writerows(harmonic_rows[i])

    print(f"Saved consolidated CSV to {csv_path}")


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if OUTPUT_CSV is None:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = os.path.join(OUTPUT_DIR, f'consolidated_no_drone_demo_{ts}.csv')
    else:
        csv_path = os.path.join(OUTPUT_DIR, OUTPUT_CSV)

    client = ViconApiClient(API_BASE_URL, BEARER_TOKEN)

    print("Checking Vicon API connection...")
    try:
        print(client.ping())
    except Exception as exc:
        print(f"ERROR: cannot reach Vicon API: {exc}")
        sys.exit(1)

    print(f"Connecting to NDT sensor on '{NDT_PORT}' ...")
    try:
        ps = PacketSerial(NDT_PORT, NDT_BAUD, timeout=0.1)
    except Exception as exc:
        print(f"ERROR: cannot open NDT sensor on '{NDT_PORT}': {exc}")
        sys.exit(1)
    _enable_streaming(ps)
    print("NDT streaming enabled.")

    vl53 = _init_laser_sensor()

    print("Sending Vicon START...")
    try:
        print(client.start(TRIAL_NAME, duration=None))
    except Exception as exc:
        _disable_streaming(ps)
        print(f"ERROR: failed to start Vicon recording: {exc}")
        sys.exit(1)

    print(
        "\nLogging started. Press Ctrl+C to stop and generate heatmap.\n"
        f"Output CSV: {csv_path}\n"
    )

    latest_x = None
    latest_y = None
    latest_laser_cm = None
    latest_pose: Dict[str, Optional[float]] = {'x': None, 'y': None}
    pose_lock = threading.Lock()
    vicon_stop_event = threading.Event()
    vicon_thread = threading.Thread(
        target=_vicon_poll_worker,
        args=(
            client,
            INCLUDE_ROTATION,
            VICON_POLL_INTERVAL_S,
            vicon_stop_event,
            latest_pose,
            pose_lock,
        ),
        daemon=True,
    )
    vicon_thread.start()

    capture_rows = []
    harmonic_plot_records = []
    harmonic_rows = {0: [], 1: [], 2: [], 3: []}

    ndt_packet_count = 0
    harmonic_packet_count = 0
    dropped_packet_count = 0

    try:
        while True:
            with pose_lock:
                latest_x = latest_pose['x']
                latest_y = latest_pose['y']

            if vl53 is not None:
                try:
                    if vl53.data_ready:
                        latest_laser_cm = float(vl53.distance)
                        vl53.clear_interrupt()
                except Exception:
                    pass

            try:
                pkt = ps.receive()
            except ValueError:
                dropped_packet_count += 1
                continue
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

            h0 = harmonics[0]['mag'] if len(harmonics) > 0 else float('nan')
            h1 = harmonics[1]['mag'] if len(harmonics) > 1 else float('nan')
            h2 = harmonics[2]['mag'] if len(harmonics) > 2 else float('nan')
            h3 = harmonics[3]['mag'] if len(harmonics) > 3 else float('nan')
            sample_no = len(capture_rows) + 1

            for i in range(4):
                if i < len(harmonics):
                    hi = harmonics[i]
                    harmonic_rows[i].append((ts_str, sample_no, hi['real'], hi['imag'], hi['mag']))

            laser_text = '' if latest_laser_cm is None else f'{latest_laser_cm:.3f}'
            capture_rows.append(
                [
                    ts_str,
                    f'{latest_x:.4f}',
                    f'{latest_y:.4f}',
                    f'{mag:.6f}',
                    laser_text,
                ]
            )
            harmonic_plot_records.append((sample_no, h0, h1, h2, h3))

            if sample_no == 1 or (sample_no % PRINT_EVERY_N_SAMPLES) == 0:
                print(
                    f"\rx={latest_x:7.3f} m  y={latest_y:7.3f} m  "
                    f"mag={mag:9.4f}  laser_cm={laser_text or 'n/a':>7}  "
                    f"samples={len(capture_rows)}",
                    end='',
                    flush=True,
                )

    except KeyboardInterrupt:
        print("\nCapture stopped by user.")
    finally:
        vicon_stop_event.set()
        vicon_thread.join(timeout=1.0)
        _disable_streaming(ps)
        print("Sending Vicon STOP...")
        try:
            print(client.stop(reason="Consolidated no-drone demo finished"))
        except Exception as exc:
            print(f"Warning: failed to stop Vicon recording cleanly: {exc}")

    print(
        f"\nCapture complete. {len(capture_rows)} samples captured "
        f"(NDT packets={ndt_packet_count}, harmonic packets={harmonic_packet_count}, "
        f"dropped packets={dropped_packet_count})."
    )

    _write_consolidated_csv(csv_path, capture_rows, harmonic_rows)

    _plot_harmonics_figure(harmonic_plot_records, csv_path)

    if len(capture_rows) < 4:
        print("Not enough data to generate heatmap (< 4 samples).")
        return

    xs = [float(r[1]) for r in capture_rows]
    ys = [float(r[2]) for r in capture_rows]
    mags = [float(r[3]) for r in capture_rows]
    _plot_heatmap(xs, ys, mags, csv_path)


if __name__ == '__main__':
    main()
