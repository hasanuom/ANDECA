#!/usr/bin/env python3
"""Fast matplotlib plotter - minimal real/imaginary visualization.

Usage:
    python3 monitor_harmonics_fast.py /dev/ttyUSB0 --baud 1000000

Single simple plot of harmonics in the complex plane - no stuttering.
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
    """Parse harmonics payload into list of (real, imag) complex pairs."""
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
        magnitude = math.sqrt(real**2 + imag**2)
        harmonics.append({'real': real, 'imag': imag, 'mag': magnitude})
    return harmonics


class FastHarmonicsPlotter:
    """Minimal, fast real-time harmonics plotter."""
    
    def __init__(self, port, baud, harmonic_idx=2):
        self.port = port
        self.baud = baud
        self.harmonic_idx = harmonic_idx
        self.pkt_count = 0
        
        # Data storage
        self.reals = deque(maxlen=100)
        self.imags = deque(maxlen=100)
        
        # Setup serial
        self.ps = None
        self.setup_serial()
        
        # Setup plot (single, simple)
        self.fig, self.ax = plt.subplots(figsize=(8, 8))
        self.fig.suptitle(f"Harmonics H{harmonic_idx} - {port} @ {baud}")
        
        self.ax.set_xlabel('Real')
        self.ax.set_ylabel('Imaginary')
        self.ax.set_title('Complex Plane')
        self.ax.grid(True, alpha=0.3)
        self.ax.axhline(y=0, color='k', linewidth=0.5)
        self.ax.axvline(x=0, color='k', linewidth=0.5)
        
        # Single scatter plot object
        self.scatter = self.ax.scatter([], [], c='blue', s=20, alpha=0.6)
        
        plt.tight_layout()
    
    def setup_serial(self):
        """Initialize serial and enable streaming."""
        try:
            self.ps = PacketSerial(self.port, self.baud, timeout=0.5)
        except Exception as e:
            print(f"Failed to open {self.port}: {e}", file=sys.stderr)
            sys.exit(1)
        
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
            time.sleep(0.2)
        except Exception as e:
            print(f"Error enabling streaming: {e}", file=sys.stderr)
    
    def update(self, frame):
        """Update callback - very minimal."""
        try:
            pkt = self.ps.receive()
        except Exception:
            return [self.scatter]
        
        if pkt is None or (pkt.command & ~GET_MASK) != PAC_ID_HARMONICS_RX:
            return [self.scatter]
        
        try:
            harmonics = parse_harmonics(pkt.payload)
        except Exception:
            return [self.scatter]
        
        self.pkt_count += 1
        
        if self.harmonic_idx < len(harmonics):
            h = harmonics[self.harmonic_idx]
            self.reals.append(h['real'])
            self.imags.append(h['imag'])
        
        # Update scatter (one operation)
        if self.reals and self.imags:
            self.scatter.set_offsets(np.column_stack([
                list(self.reals), 
                list(self.imags)
            ]))
        
        # Update title every 10 frames
        if self.pkt_count % 10 == 0 and self.reals:
            mag = math.sqrt(self.reals[-1]**2 + self.imags[-1]**2)
            self.fig.suptitle(
                f"H{self.harmonic_idx} - pkt#{self.pkt_count} - mag={mag:.1f}"
            )
        
        # Auto-scale seldomly
        if self.pkt_count % 30 == 0:
            self.ax.autoscale_view()
        
        return [self.scatter]
    
    def run(self):
        """Start animation."""
        ani = animation.FuncAnimation(
            self.fig, self.update,
            interval=20,  # 20ms = 50 Hz
            blit=True, cache_frame_data=False
        )
        
        print("Fast harmonics plotter running (blitted)...")
        try:
            plt.show()
        except KeyboardInterrupt:
            pass
        finally:
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
            self.ps.close()


def main():
    parser = argparse.ArgumentParser(description="Fast harmonics plotter (minimal matplotlib).")
    parser.add_argument("port", help="Serial port")
    parser.add_argument("--baud", type=int, default=1000000, help="Baud rate")
    parser.add_argument("--harmonic", type=int, default=2, help="Harmonic index to plot")
    
    args = parser.parse_args()
    
    plotter = FastHarmonicsPlotter(args.port, args.baud, args.harmonic)
    plotter.run()


if __name__ == '__main__':
    main()
