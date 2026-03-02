"""Configure the NDT sensor then capture incoming packets to CSV.

Usage examples:
  # configure a single TX harmonic at 1000 Hz then capture 100 packets
  python3 capture_and_save.py /dev/ttyUSB0 out.csv --baud 1000000 --freq 1000 --count 100

  # configure with default harmonics and capture for 10 seconds
  python3 capture_and_save.py /dev/ttyUSB0 out.csv --baud 1000000 --duration 10
"""
from __future__ import annotations
import time
import argparse
import csv
from typing import List, Tuple, Optional

from packet import Packet, PacketSerial, make_tx_config_payload
import pac_ids as ids
from pac_handlers import parse_packet


def configure_sensor(link: PacketSerial, seq_start: int, enable_mask: int, scale: float, harmonics: List[Tuple[int, float, float]]) -> int:
    """Send a TX configuration packet. Returns next sequence number."""
    payload = make_tx_config_payload(enable_mask, scale, harmonics)
    pkt = Packet(
        device_address=ids.DEFAULT_DEVICE_ADDRESS,
        command=ids.PAC_ID_TX_CONFIGURATION | ids.SET_MASK,
        seq_num=seq_start,
        payload=payload,
    )
    link.send(pkt)
    # attempt to read any immediate response (may be None)
    _ = link.receive()
    return seq_start + 1


def capture_loop(link: PacketSerial, out_csv: str, max_count: Optional[int], max_duration: Optional[float]) -> None:
    start = time.time()
    written = 0
    with open(out_csv, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "cmd", "seq", "sample_index", "value", "raw"])
        while True:
            if max_count is not None and written >= max_count:
                break
            if max_duration is not None and (time.time() - start) >= max_duration:
                break
            pkt = link.receive()
            if pkt is None:
                continue
            ts = time.time()
            parsed = parse_packet(pkt)
            cmd_hex = f"0x{pkt.command:04X}"
            if isinstance(parsed, list) and parsed and isinstance(parsed[0], float):
                for i, v in enumerate(parsed):
                    writer.writerow([ts, cmd_hex, pkt.seq_num, i, f"{v:.6f}", ""])
                written += 1
            else:
                # non-sample payload: write one row with raw hex
                raw = parsed if not isinstance(parsed, list) else ",".join(str(x) for x in parsed)
                writer.writerow([ts, cmd_hex, pkt.seq_num, "", "", raw])
                written += 1


def main() -> None:
    p = argparse.ArgumentParser(description="Configure NDT sensor and capture packets to CSV")
    p.add_argument("port")
    p.add_argument("out_csv")
    p.add_argument("--baud", type=int, default=1000000)
    p.add_argument("--duration", type=float, default=None, help="Capture duration in seconds")
    p.add_argument("--count", type=int, default=None, help="Number of packets to capture")
    p.add_argument("--freq", type=float, default=None, help="Single harmonic frequency to configure (Hz)")
    p.add_argument("--enable-mask", type=int, default=0x0001, help="Enable mask for TX config")
    p.add_argument("--scale", type=float, default=1.0, help="Scale for TX config")
    args = p.parse_args()

    link = PacketSerial(args.port, baudrate=args.baud, timeout=0.5)
    seq = 1

    harmonics: List[Tuple[int, float, float]] = []
    if args.freq is not None:
        # create a single harmonic with mag=1.0 and phase=0.0
        harmonics.append((int(args.freq), 1.0, 0.0))

    if harmonics:
        seq = configure_sensor(link, seq, args.enable_mask, args.scale, harmonics)

    try:
        capture_loop(link, args.out_csv, args.count, args.duration)
    except KeyboardInterrupt:
        print("capture interrupted")


if __name__ == "__main__":
    main()
