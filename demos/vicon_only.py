#!/usr/bin/env python3
"""Vicon-only capture demo.

This script mirrors the Vicon polling workflow used in no_drone_demo.py, but
removes all NDT logic.

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
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import matplotlib.pyplot as plt
import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------

API_BASE_URL = "http://192.168.10.1:8080"
BEARER_TOKEN = "changeme"
TRIAL_NAME = "Vicon_Only"

VICON_POLL_INTERVAL_S = 0.05
INCLUDE_ROTATION = False
PRINT_EVERY_N_SAMPLES = 10

OUTPUT_DIR = '/media/andeca/ENUODA/readings/vicon_only'
OUTPUT_CSV = None
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
    ax.set_title(f'Vicon XY Plane, {len(xs)} samples')
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


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if OUTPUT_CSV is None:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = os.path.join(OUTPUT_DIR, f'vicon_only_{ts}.csv')
    else:
        csv_path = os.path.join(OUTPUT_DIR, OUTPUT_CSV)

    client = ViconApiClient(API_BASE_URL, BEARER_TOKEN)

    print("Checking Vicon API connection...")
    try:
        print(client.ping())
    except Exception as exc:
        print(f"ERROR: cannot reach Vicon API: {exc}")
        sys.exit(1)

    vl53 = _init_laser_sensor()

    print("Sending Vicon START...")
    try:
        print(client.start(TRIAL_NAME, duration=None))
    except Exception as exc:
        print(f"ERROR: failed to start Vicon recording: {exc}")
        sys.exit(1)

    print(
        "\nLogging started. Press Ctrl+C to stop and generate the XY plot.\n"
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

    rows = []
    sample_count = 0
    last_diag = time.time()

    try:
        with open(csv_path, 'w', newline='') as fh:
            writer = csv.writer(fh)
            writer.writerow(['timestamp', 'x_m', 'y_m', 'laser_distance_cm'])

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

                if latest_x is None or latest_y is None:
                    if (time.time() - last_diag) >= 3.0:
                        print("Waiting for Vicon pose data...")
                        last_diag = time.time()
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

    except KeyboardInterrupt:
        print("\nCapture stopped by user.")
    finally:
        vicon_stop_event.set()
        vicon_thread.join(timeout=1.0)
        print("Sending Vicon STOP...")
        try:
            print(client.stop(reason="Vicon-only demo finished"))
        except Exception as exc:
            print(f"Warning: failed to stop Vicon recording cleanly: {exc}")

    print(f"\nCapture complete. {len(rows)} samples written to {csv_path}.")

    if len(rows) < 2:
        print("Not enough data to generate XY plot.")
        return

    xs = [r[0] for r in rows]
    ys = [r[1] for r in rows]
    _plot_xy_path(xs, ys, csv_path)


if __name__ == '__main__':
    main()
