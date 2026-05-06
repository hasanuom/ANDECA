#!/usr/bin/env python3
"""Generate a NDT heatmap from a previously saved demo CSV file.

Usage:
    python3 heatmap_from_csv.py /path/to/readings/file.csv

The CSV must contain at minimum the columns produced by drone_demo.py and
no_drone_demo.py:
    timestamp, x_m, y_m, magnitude_h<N>, laser_distance_cm

The heatmap PNG is saved to /media/andeca/ENUODA/readings/heatmap_from_csv/
alongside a copy of the source filename for easy identification.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys

import matplotlib.pyplot as plt
import numpy as np


OUTPUT_DIR = '/media/andeca/ENUODA/readings/heatmap_from_csv'
HEATMAP_RESOLUTION = 50
SHOW_INTERACTIVE_PLOT = True


def _plot_heatmap(xs: list, ys: list, mags: list, out_path: str, n_samples: int) -> None:
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
    plt.colorbar(im, ax=ax, label='NDT Magnitude')
    ax.scatter(xs_arr, ys_arr, s=2, c='cyan', alpha=0.25, label='Sample positions')

    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_title(f'NDT Heatmap from CSV — {n_samples} samples')
    ax.legend(fontsize=8, loc='upper right')

    fig.savefig(out_path, dpi=150, bbox_inches='tight')
    print(f"Heatmap saved to {out_path}")

    if SHOW_INTERACTIVE_PLOT:
        plt.show()
    else:
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate NDT heatmap from a demo CSV file."
    )
    parser.add_argument('csv_file', help='Path to the CSV file to process.')
    args = parser.parse_args()

    csv_path = args.csv_file
    if not os.path.isfile(csv_path):
        print(f"ERROR: file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    xs = []
    ys = []
    mags = []
    mag_col = None

    with open(csv_path, newline='') as fh:
        reader = csv.DictReader(fh)
        headers = reader.fieldnames or []

        # Find the magnitude column — named magnitude_h<N>
        for h in headers:
            if h.startswith('magnitude_h'):
                mag_col = h
                break

        if mag_col is None:
            print(
                f"ERROR: no 'magnitude_h*' column found in {csv_path}.\n"
                f"Available columns: {headers}",
                file=sys.stderr,
            )
            sys.exit(1)

        if 'x_m' not in headers or 'y_m' not in headers:
            print(
                f"ERROR: CSV must have 'x_m' and 'y_m' columns.\n"
                f"Available columns: {headers}",
                file=sys.stderr,
            )
            sys.exit(1)

        for row in reader:
            try:
                x = float(row['x_m'])
                y = float(row['y_m'])
                m = float(row[mag_col])
                if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(m)):
                    continue
                xs.append(x)
                ys.append(y)
                mags.append(m)
            except (ValueError, KeyError):
                continue

    print(f"Loaded {len(xs)} valid samples from {csv_path} (magnitude column: '{mag_col}').")

    if len(xs) < 4:
        print("Not enough data to generate heatmap (< 4 valid samples).")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(csv_path))[0]
    out_path = os.path.join(OUTPUT_DIR, f'{base}_heatmap.png')

    _plot_heatmap(xs, ys, mags, out_path, len(xs))


if __name__ == '__main__':
    main()
