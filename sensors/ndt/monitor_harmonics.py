#!/usr/bin/env python3
"""Monitor harmonics in real-time, showing real/imaginary components.

Usage:
    python3 monitor_harmonics.py /dev/ttyUSB0 --baud 1000000 --poll-interval 0.1

Displays real and imaginary parts of the 5th harmonic per second,
making it easy to see when metal is moved near the sensor.
"""

import argparse
import sys
import time
import struct
import math
from datetime import datetime

from packet import PacketSerial
from pac_ids import GET_MASK, PAC_ID_HARMONICS_RX
from pac_handlers import parse_packet


def parse_harmonics(data):
    """Parse harmonics payload into list of (real, imag) complex pairs.
    
    Harmonics are stored as interleaved float pairs: real0, imag0, real1, imag1, ...
    Each float is in TI DSP middle-endian format.
    """
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


def format_complex(val):
    """Format a complex number nicely."""
    return f"{val['real']:8.1f} + {val['imag']:8.1f}j  (mag={val['mag']:8.1f})"


def main():
    parser = argparse.ArgumentParser(
        description="Monitor harmonics data in real-time."
    )
    parser.add_argument("port", help="Serial port (e.g., /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=1000000,
                        help="Baud rate (default: 1000000)")
    parser.add_argument("--poll-interval", type=float, default=0.1,
                        help="Polling interval in seconds (default: 0.1)")
    parser.add_argument("--baseline-secs", type=float, default=3.0,
                        help="Collect baseline for N seconds (default: 3)")
    parser.add_argument("--alert-mult", type=float, default=3.0,
                        help="Alert threshold as multiple of baseline std dev (default: 3)")
    parser.add_argument("--harmonic", type=int, default=0,
                        help="Harmonic index to highlight (0=fundamental, default: 0)")
    
    args = parser.parse_args()
    
    try:
        # Use a shorter timeout to match polling interval for responsiveness
        timeout = min(args.poll_interval * 2, 0.5)
        ps = PacketSerial(args.port, args.baud, timeout=timeout)
    except Exception as e:
        print(f"Failed to open {args.port}: {e}", file=sys.stderr)
        sys.exit(1)
    
    print(f"listening {args.port} @ {args.baud}, ctrl-C to stop")
    print(f"requesting harmonics packet (ID=0x{PAC_ID_HARMONICS_RX:04x})")
    print()
    
    # Build GET request for harmonics
    from packet import Packet
    req = Packet(
        device_address=0,
        command=GET_MASK | PAC_ID_HARMONICS_RX,
        seq_num=0,
        payload=b''
    )
    
    baseline_mags = []
    baseline_time = time.time()
    baseline_duration = args.baseline_secs
    baseline_done = False
    baseline_mean = None
    baseline_std = None
    
    pkt_count = 0
    harmonic_idx = args.harmonic
    last_alert_time = 0  # Suppress repeated alerts
    
    try:
        while True:
            # Send GET request
            try:
                ps.send(req)
            except Exception as e:
                print(f"Error sending request: {e}", file=sys.stderr)
                continue
            
            # Small inter-request delay to avoid overwhelming serial
            time.sleep(args.poll_interval * 0.5)
            
            # Wait for response with short timeout
            try:
                pkt = ps.receive()
            except Exception:
                # Timeout or serial error - just retry
                continue
            
            # Skip if no packet received (timeout)
            if pkt is None:
                continue
            
            pkt_count += 1
            
            # Check if it's a harmonics response
            if (pkt.command & ~GET_MASK) != PAC_ID_HARMONICS_RX:
                continue
            
            try:
                harmonics = parse_harmonics(pkt.payload)
            except Exception as e:
                print(f"Error parsing harmonics: {e}", file=sys.stderr)
                continue
            
            now = datetime.now()
            elapsed_baseline = time.time() - baseline_time
            
            # Print all harmonics
            print(f"{now.strftime('%H:%M:%S')} pkt#{pkt_count:4d}  Harmonics (0=fund, 1=3rd, 2=5th, ...):")
            for idx, h in enumerate(harmonics[:8]):  # Show first 8
                mark = " <-- WATCHING" if idx == harmonic_idx else ""
                print(f"  H{idx:2d}: {format_complex(h)}{mark}")
            
            # Collect baseline magnetude for the selected harmonic
            if harmonic_idx < len(harmonics):
                mag = harmonics[harmonic_idx]['mag']
                baseline_mags.append(mag)
                
                if not baseline_done and elapsed_baseline < baseline_duration:
                    print(f"       (baseline {elapsed_baseline:.1f}/{baseline_duration}s)")
                elif not baseline_done:
                    baseline_done = True
                    baseline_mean = sum(baseline_mags) / len(baseline_mags)
                    baseline_std = math.sqrt(
                        sum((x - baseline_mean)**2 for x in baseline_mags) / len(baseline_mags)
                    )
                    print(f"       Baseline: mean={baseline_mean:.1f}, std={baseline_std:.1f}")
                    print()
                elif baseline_done:
                    # Check for alert (suppress repeated alerts to reduce spam)
                    threshold = baseline_mean + args.alert_mult * baseline_std
                    current_time = time.time()
                    if mag > threshold and (current_time - last_alert_time) > 0.5:
                        print(f"       *** ALERT! magnitude {mag:.1f} > threshold {threshold:.1f} ***")
                        last_alert_time = current_time
            
            print()
    
    except KeyboardInterrupt:
        print("\nstopped")
        ps.close()
        sys.exit(0)


if __name__ == '__main__':
    main()
