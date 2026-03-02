#!/usr/bin/env python3
"""Fast matplotlib magnitude live plotting with proper blitting.

Usage:
    python3 monitor_live_realimag_fast.py /dev/ttyUSB0 --baud 1000000 --harmonic 2

Single magnitude plot updated in real-time using matplotlib blitting
(only changed artists redrawn). Zero lag, smooth updates.
"""

import argparse
import sys
import time
import struct
import math
from collections import deque

import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np

from packet import PacketSerial, Packet
from pac_ids import GET_MASK, SET_MASK, PAC_ID_HARMONICS_RX, PAC_ID_SETTINGS_STREAMING


def parse_harmonics(data):
    n_floats = len(data) // 4
    bigendian = bytearray(0)
    for i in range(0, len(data), 4):
        lsword = data[i : i + 2]
        word = data[i + 2 : i + 4] + lsword
        bigendian += word
    floats = list(struct.unpack(f">{n_floats}f", bytes(bigendian)))
    harmonics = []
    for i in range(0, len(floats), 2):
        real = floats[i]
        imag = floats[i + 1] if i + 1 < len(floats) else 0.0
        mag = math.sqrt(real * real + imag * imag)
        harmonics.append({'real': real, 'imag': imag, 'mag': mag})
    return harmonics


class FastRealImagPlotter:
    """Minimal, blitted matplotlib plotter for magnitude only."""
    
    def __init__(self, port, baud, harmonic_idx=2, history=100):
        self.port = port
        self.baud = baud
        self.harmonic_idx = harmonic_idx
        
        # Data storage
        self.times = deque(maxlen=history)
        self.mags = deque(maxlen=history)
        
        self.pkt_count = 0
        
        # Setup serial
        self.ps = None
        self.setup_serial()
        
        # Setup plotting (single plot)
        self.fig, self.ax = plt.subplots(figsize=(10, 5))
        self.fig.suptitle(f"H{harmonic_idx} Magnitude - {port} @ {baud}")
        
        # Mag subplot
        self.ax.set_ylabel('Magnitude')
        self.ax.set_xlabel('Packet #')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_ylim(-10, 100)  # Initial range, will auto-adjust
        self.line_mag, = self.ax.plot([], [], 'g-', linewidth=1.5)
        
        plt.tight_layout()
    
    def setup_serial(self):
        try:
            self.ps = PacketSerial(self.port, self.baud, timeout=0.3)
        except Exception as e:
            print(f"Failed to open: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Enable streaming
        stream_enable = 4
        payload = struct.pack(">B", stream_enable)
        req = Packet(
            device_address=0,
            command=SET_MASK | PAC_ID_SETTINGS_STREAMING,
            seq_num=0,
            payload=payload
        )
        try:
            self.ps.send(req)
            time.sleep(0.2)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
    
    def update(self, frame):
        """Update callback - magnitude only."""
        try:
            pkt = self.ps.receive()
        except Exception:
            pkt = None
        
        if pkt is None:
            return []
        
        if (pkt.command & ~GET_MASK) != PAC_ID_HARMONICS_RX:
            return []
        
        try:
            harmonics = parse_harmonics(pkt.payload)
        except Exception:
            return []
        
        self.pkt_count += 1
        
        if self.harmonic_idx < len(harmonics):
            h = harmonics[self.harmonic_idx]
            self.times.append(self.pkt_count)
            self.mags.append(h['mag'])
        else:
            return []
        
        # Convert to numpy arrays
        times_arr = np.array(list(self.times), dtype=np.float32)
        mags_arr = np.array(list(self.mags), dtype=np.float32)
        
        # Update line data (very fast)
        self.line_mag.set_data(times_arr, mags_arr)
        
        # Auto-scale every 20 frames
        if self.pkt_count % 20 == 0:
            if len(mags_arr) > 0:
                y_min = min(mags_arr)
                y_max = max(mags_arr)
                y_pad = (y_max - y_min) * 0.1 if y_max > y_min else 5
                self.ax.set_ylim([y_min - y_pad, y_max + y_pad])
                self.ax.set_xlim([times_arr[0], times_arr[-1] + 5])
        
        # Update title every 10 frames
        if self.pkt_count % 10 == 0:
            mag = self.mags[-1] if self.mags else 0
            self.fig.suptitle(
                f"H{self.harmonic_idx} | pkt {self.pkt_count} | mag={mag:.1f}"
            )
        
        # Return changed artists for blitting
        return [self.line_mag]
    
    def run(self):
        """Start animation with blitting."""
        ani = animation.FuncAnimation(
            self.fig, self.update,
            interval=20,  # 20ms = 50 Hz
            blit=True, cache_frame_data=False
        )
        
        print("Real/Imag/Mag plotter running (fast)...")
        try:
            plt.show()
        except KeyboardInterrupt:
            pass
        finally:
            try:
                off = struct.pack(">B", 0)
                stop = Packet(
                    device_address=0,
                    command=SET_MASK | PAC_ID_SETTINGS_STREAMING,
                    seq_num=0,
                    payload=off
                )
                self.ps.send(stop)
            except Exception:
                pass
            try:
                self.ps.ser.close()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="Fast magnitude plotter with blitting."
    )
    parser.add_argument("port", help="Serial port")
    parser.add_argument("--baud", type=int, default=1000000, help="Baud rate")
    parser.add_argument("--harmonic", type=int, default=2, help="Harmonic to plot")
    parser.add_argument("--history", type=int, default=100,
                        help="Number of samples in history")
    
    args = parser.parse_args()
    
    plotter = FastRealImagPlotter(args.port, args.baud, args.harmonic, args.history)
    plotter.run()


if __name__ == '__main__':
    main()
