#!/usr/bin/env python3
"""Real-time harmonics plotter with complex plane visualization.

Usage:
    python3 monitor_harmonics_plot.py /dev/ttyUSB0 --baud 1000000

Displays:
- Left: Complex plane scatter (real vs imaginary) for each harmonic
- Right: Time series of magnitude for the selected harmonic
"""

import argparse
import sys
import time
import struct
import math
from datetime import datetime
from collections import deque

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np

from packet import PacketSerial, Packet
from pac_ids import GET_MASK, SET_MASK, PAC_ID_HARMONICS_RX, PAC_ID_SETTINGS_STREAMING


def parse_harmonics(data):
    """Parse harmonics payload into list of (real, imag) complex pairs."""
    n_floats = len(data) // 4
    
    # Convert middle-endian floats to big-endian floats
    bigendian = bytearray(0)
    for i in range(0, len(data), 4):
        lsword = data[i : i + 2]
        word = data[i + 2 : i + 4] + lsword
        bigendian += word
    
    floats = list(struct.unpack(f">{n_floats}f", bytes(bigendian)))
    
    # Pair into (real, imag) tuples
    harmonics = []
    for i in range(0, len(floats), 2):
        real = floats[i]
        imag = floats[i + 1] if i + 1 < len(floats) else 0.0
        magnitude = math.sqrt(real**2 + imag**2)
        phase = math.atan2(imag, real)
        harmonics.append({
            'real': real,
            'imag': imag,
            'mag': magnitude,
            'phase': phase
        })
    return harmonics


class HarmonicsPlotter:
    """Fast real-time harmonics plotter with optimized rendering."""
    
    def __init__(self, port, baud, harmonic_idx=2, max_history=200):
        self.port = port
        self.baud = baud
        self.harmonic_idx = harmonic_idx
        self.max_history = max_history
        
        # Data storage: deques for efficient rolling window
        self.times = deque(maxlen=max_history)
        self.magnitudes = deque(maxlen=max_history)
        
        # Track multiple harmonics for complex plane
        self.harmonic_sets = {}  # idx -> {'reals': deque, 'imags': deque, 'color': str, 'scatter': obj}
        colors = ['red', 'green', 'blue', 'orange', 'purple', 'brown', 'pink', 'gray']
        for i in range(8):
            self.harmonic_sets[i] = {
                'reals': deque(maxlen=max_history),
                'imags': deque(maxlen=max_history),
                'color': colors[i % len(colors)],
                'scatter': None
            }
        
        self.pkt_count = 0
        self.baseline_mean = None
        self.baseline_std = None
        
        # Setup serial
        self.ps = None
        self.setup_serial()
        
        # Setup plotting
        self.fig, (self.ax_complex, self.ax_time) = plt.subplots(
            1, 2, figsize=(14, 6)
        )
        self.fig.suptitle(
            f"Harmonics Monitor (H{harmonic_idx}: 5th, 3rd, fund, etc...) | "
            f"{port} @ {baud} baud",
            fontsize=12
        )
        
        # Complex plane setup (persistent)
        self.ax_complex.set_xlabel('Real')
        self.ax_complex.set_ylabel('Imaginary')
        self.ax_complex.set_title('Complex Plane (Harmonics Scatter)')
        self.ax_complex.grid(True, alpha=0.3)
        self.ax_complex.axhline(y=0, color='k', linewidth=0.5)
        self.ax_complex.axvline(x=0, color='k', linewidth=0.5)
        
        # Time domain setup (persistent)
        self.ax_time.set_xlabel('Time (samples)')
        self.ax_time.set_ylabel('Magnitude')
        self.ax_time.set_title(f'Magnitude vs Time (H{harmonic_idx})')
        self.ax_time.grid(True, alpha=0.3)
        
        # Create initial plot objects that we'll update (don't recreate each frame)
        self.line_mag, = self.ax_time.plot([], [], 'b-', linewidth=1.5, label='Magnitude')
        self.baseline_line = None
        self.baseline_fill = None
        self.alert_scatter = self.ax_time.scatter([], [], color='red', s=100, marker='*', zorder=5)
        
        # Create scatter for each harmonic (reuse these objects)
        for idx in range(8):
            scatter = self.ax_complex.scatter([], [], c=self.harmonic_sets[idx]['color'], 
                                             s=30, alpha=0.6, label=f'H{idx}')
            self.harmonic_sets[idx]['scatter'] = scatter
        
        self.ax_time.legend(loc='upper left', fontsize=8)
        
        plt.tight_layout()
    
    def setup_serial(self):
        """Initialize serial connection and enable streaming."""
        try:
            self.ps = PacketSerial(self.port, self.baud, timeout=0.5)
        except Exception as e:
            print(f"Failed to open {self.port}: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Enable streaming RXV (receive harmonics) - bit 2 = value 4
        stream_enable = 4
        stream_payload = struct.pack(">B", stream_enable)
        
        stream_req = Packet(
            device_address=0,
            command=SET_MASK | PAC_ID_SETTINGS_STREAMING,
            seq_num=0,
            payload=stream_payload
        )
        
        try:
            self.ps.send(stream_req)
            time.sleep(0.5)
        except Exception as e:
            print(f"Error enabling streaming: {e}", file=sys.stderr)
    
    def update_plot(self, frame):
        """Animation callback - fetch data and update plots (optimized for speed)."""
        # Try to receive a packet
        try:
            pkt = self.ps.receive()
        except Exception:
            return [self.line_mag]
        
        if pkt is None:
            return [self.line_mag]
        
        # Check if it's a harmonics response
        if (pkt.command & ~GET_MASK) != PAC_ID_HARMONICS_RX:
            return [self.line_mag]
        
        # Parse harmonics
        try:
            harmonics = parse_harmonics(pkt.payload)
        except Exception as e:
            print(f"Error parsing harmonics: {e}", file=sys.stderr)
            return [self.line_mag]
        
        self.pkt_count += 1
        
        # Store data
        self.times.append(self.pkt_count)
        
        # Store all harmonics
        for idx, h in enumerate(harmonics):
            if idx < 8:
                self.harmonic_sets[idx]['reals'].append(h['real'])
                self.harmonic_sets[idx]['imags'].append(h['imag'])
        
        # Track selected harmonic for time series
        if self.harmonic_idx < len(harmonics):
            mag = harmonics[self.harmonic_idx]['mag']
            self.magnitudes.append(mag)
        
        # Update baseline statistics (first 60 packets)
        if self.pkt_count <= 60 and self.magnitudes:
            mags = list(self.magnitudes)
            self.baseline_mean = sum(mags) / len(mags)
            self.baseline_std = math.sqrt(
                sum((x - self.baseline_mean)**2 for x in mags) / len(mags)
            ) if len(mags) > 1 else 0.1
        
        # ===== Update Complex Plane (reuse scatter objects, no clearing) =====
        for idx in range(8):
            reals = np.array(list(self.harmonic_sets[idx]['reals']), dtype=np.float32)
            imags = np.array(list(self.harmonic_sets[idx]['imags']), dtype=np.float32)
            
            if len(reals) > 0:
                # Update scatter offsets instead of recreating
                offsets = np.column_stack([reals, imags])
                self.harmonic_sets[idx]['scatter'].set_offsets(offsets)
                
                # Update alpha based on position (fade old points)
                alphas = np.linspace(0.2, 0.8, len(reals))
                self.harmonic_sets[idx]['scatter'].set_alpha(np.mean(alphas))
        
        # Auto-scale complex plane every 30 packets
        if self.pkt_count % 30 == 0 and self.pkt_count > 5:
            self.ax_complex.autoscale_view()
        
        # ===== Update Time Series (reuse line objects) =====
        if self.magnitudes:
            times_list = np.array(list(self.times), dtype=np.float32)
            mags_list = np.array(list(self.magnitudes), dtype=np.float32)
            
            # Update line data (fast)
            self.line_mag.set_data(times_list, mags_list)
            
            # Update baseline and alert visualization every 20 packets (not every frame)
            if self.pkt_count % 20 == 0:
                # Remove old baseline elements
                if self.baseline_line is not None:
                    self.baseline_line.remove()
                if self.baseline_fill is not None:
                    self.baseline_fill.remove()
                
                # Redraw baseline
                if self.baseline_mean is not None and self.baseline_std is not None:
                    lower = self.baseline_mean - 3 * self.baseline_std
                    upper = self.baseline_mean + 3 * self.baseline_std
                    self.baseline_line = self.ax_time.axhline(
                        y=self.baseline_mean, color='g', linestyle='--', 
                        linewidth=1, label=f'Baseline: {self.baseline_mean:.1f}'
                    )
                    self.baseline_fill = self.ax_time.fill_between(
                        times_list, lower, upper, color='green', alpha=0.1
                    )
                
                # Update alert scatter
                alert_times = []
                alert_mags = []
                if self.baseline_mean is not None and self.baseline_std is not None:
                    threshold = self.baseline_mean + 3 * self.baseline_std
                    for t, m in zip(times_list, mags_list):
                        if m > threshold:
                            alert_times.append(t)
                            alert_mags.append(m)
                
                if alert_times:
                    self.alert_scatter.set_offsets(np.column_stack([alert_times, alert_mags]))
                else:
                    self.alert_scatter.set_offsets(np.empty((0, 2)))
                
                # Auto-scale y axis
                all_vals = list(mags_list)
                if self.baseline_mean is not None:
                    all_vals.append(self.baseline_mean + 5 * self.baseline_std)
                
                if len(all_vals) > 0:
                    y_max = max(all_vals)
                    y_min = min(all_vals) - 5
                    y_min = max(0, y_min)
                    self.ax_time.set_ylim([y_min, y_max * 1.1])
                    self.ax_time.set_xlim([times_list[0], times_list[-1] + 5])
        
        # Update title (only every 10 frames to reduce overhead)
        if self.pkt_count % 10 == 0:
            if self.magnitudes and self.baseline_mean is not None:
                latest_mag = self.magnitudes[-1]
                title_str = (
                    f"H{self.harmonic_idx} | pkt#{self.pkt_count:4d} | "
                    f"mag={latest_mag:.1f} | "
                    f"baseline={self.baseline_mean:.1f}±{self.baseline_std:.1f}"
                )
                self.fig.suptitle(title_str, fontsize=11)
        
        # Return artists for blitting
        artists = [self.line_mag, self.alert_scatter]
        for idx in range(8):
            if self.harmonic_sets[idx]['scatter'] is not None:
                artists.append(self.harmonic_sets[idx]['scatter'])
        
        return artists
    
    def run(self):
        """Start the animation."""
        ani = animation.FuncAnimation(
            self.fig, self.update_plot, 
            interval=30,  # 30ms between updates = faster rendering
            blit=False, cache_frame_data=False
        )
        
        print("Starting real-time harmonics plotter...")
        print("Close the plot window to exit, or press Ctrl+C in terminal.")
        
        try:
            plt.show()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Plot error: {e}", file=sys.stderr)
        finally:
            # Disable streaming
            try:
                stream_disable = 0
                disable_payload = struct.pack(">B", stream_disable)
                stop_req = Packet(
                    device_address=0,
                    command=SET_MASK | PAC_ID_SETTINGS_STREAMING,
                    seq_num=0,
                    payload=disable_payload
                )
                self.ps.send(stop_req)
            except Exception:
                pass
            
            try:
                self.ps.close()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="Real-time harmonics plotter with complex plane visualization."
    )
    parser.add_argument("port", help="Serial port (e.g., /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=1000000,
                        help="Baud rate (default: 1000000)")
    parser.add_argument("--harmonic", type=int, default=2,
                        help="Harmonic index to highlight in time series (0=fund, 1=3rd, 2=5th, default: 2)")
    parser.add_argument("--history", type=int, default=200,
                        help="Number of samples to keep in history (default: 200)")
    
    args = parser.parse_args()
    
    plotter = HarmonicsPlotter(
        args.port, args.baud, 
        harmonic_idx=args.harmonic,
        max_history=args.history
    )
    plotter.run()


if __name__ == '__main__':
    main()
