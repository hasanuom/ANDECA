#!/usr/bin/env python3
"""Real-time terminal plot of real/imaginary parts using curses (zero lag).

Usage:
    python3 monitor_live_realimag.py /dev/ttyUSB0 --baud 1000000 --harmonic 2

Shows two synchronized line plots (real, imag) updating in real-time with
no GUI overhead. Pure terminal rendering = instant updates.
"""

import argparse
import sys
import time
import struct
import math
import curses
from collections import deque

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
        harmonics.append({'real': real, 'imag': imag})
    return harmonics


class CursesPlotter:
    def __init__(self, port, baud, harmonic_idx=2, width=80, height=20):
        self.port = port
        self.baud = baud
        self.harmonic_idx = harmonic_idx
        self.width = width
        self.height = height
        
        # Data buffers (limit to width for display)
        self.reals = deque(maxlen=width - 10)
        self.imags = deque(maxlen=width - 10)
        
        # Setup serial
        self.ps = None
        self.setup_serial()
        
        self.pkt_count = 0
    
    def setup_serial(self):
        try:
            self.ps = PacketSerial(self.port, self.baud, timeout=0.1)
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
            print(f"Error enabling streaming: {e}", file=sys.stderr)
    
    def plot_line(self, values, min_val, max_val, height, width):
        """Draw a line plot from values."""
        if not values or max_val == min_val:
            return ['│' + ' ' * (width - 2) + '│' for _ in range(height)]
        
        # Normalize values to 0-1
        range_val = max_val - min_val
        normalized = [(v - min_val) / range_val for v in values]
        
        # Create grid
        grid = [[' ' for _ in range(width)] for _ in range(height)]
        
        # Plot points
        for x, norm_val in enumerate(normalized):
            y = int((1.0 - norm_val) * (height - 1))
            y = max(0, min(height - 1, y))
            if x < width - 2:
                grid[y][x + 1] = '●'
        
        # Add borders
        lines = []
        for row in grid:
            lines.append('│' + ''.join(row) + '│')
        
        return lines
    
    def run(self, stdscr):
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(True)  # Non-blocking input
        
        while True:
            # Fetch packet
            try:
                pkt = self.ps.receive()
            except Exception:
                pkt = None
            
            if pkt and (pkt.command & ~GET_MASK) == PAC_ID_HARMONICS_RX:
                try:
                    harmonics = parse_harmonics(pkt.payload)
                    if self.harmonic_idx < len(harmonics):
                        h = harmonics[self.harmonic_idx]
                        self.reals.append(h['real'])
                        self.imags.append(h['imag'])
                        self.pkt_count += 1
                except Exception:
                    pass
            
            # Check for quit
            try:
                ch = stdscr.getch()
                if ch == ord('q') or ch == 27:  # q or ESC
                    break
            except Exception:
                pass
            
            # Draw screen
            stdscr.clear()
            
            if not self.reals or not self.imags:
                stdscr.addstr(0, 0, f"Waiting for data... (pkt {self.pkt_count})")
                stdscr.refresh()
                time.sleep(0.05)
                continue
            
            # Calculate ranges
            real_vals = list(self.reals)
            imag_vals = list(self.imags)
            
            real_min, real_max = min(real_vals), max(real_vals)
            imag_min, imag_max = min(imag_vals), max(imag_vals)
            
            # Add 10% padding
            real_pad = (real_max - real_min) * 0.1 or 1
            imag_pad = (imag_max - imag_min) * 0.1 or 1
            
            real_min -= real_pad
            real_max += real_pad
            imag_min -= imag_pad
            imag_max += imag_pad
            
            plot_height = (self.height - 4) // 2 - 1
            plot_width = self.width
            
            # Plot real part
            real_lines = self.plot_line(real_vals, real_min, real_max, plot_height, plot_width)
            
            # Plot imaginary part
            imag_lines = self.plot_line(imag_vals, imag_min, imag_max, plot_height, plot_width)
            
            # Draw title
            title = f"H{self.harmonic_idx} Real/Imag (pkt {self.pkt_count}) - Press 'q' to quit"
            stdscr.addstr(0, 0, title[:self.width])
            
            # Draw real plot
            stdscr.addstr(1, 0, f"Real [{real_min:.1f}..{real_max:.1f}]:")
            for i, line in enumerate(real_lines):
                stdscr.addstr(2 + i, 0, line[:self.width])
            
            # Draw imag plot
            y_offset = 2 + plot_height + 1
            stdscr.addstr(y_offset, 0, f"Imag [{imag_min:.1f}..{imag_max:.1f}]:")
            for i, line in enumerate(imag_lines):
                stdscr.addstr(y_offset + 1 + i, 0, line[:self.width])
            
            stdscr.refresh()
            time.sleep(0.05)
    
    def cleanup(self):
        """Disable streaming and close."""
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
        description="Super-fast terminal real/imag plotter (curses-based)."
    )
    parser.add_argument("port", help="Serial port")
    parser.add_argument("--baud", type=int, default=1000000, help="Baud rate")
    parser.add_argument("--harmonic", type=int, default=2, help="Harmonic index")
    
    args = parser.parse_args()
    
    plotter = CursesPlotter(args.port, args.baud, args.harmonic)
    
    try:
        curses.wrapper(plotter.run)
    except KeyboardInterrupt:
        pass
    finally:
        plotter.cleanup()
        print("Stopped")


if __name__ == '__main__':
    main()
