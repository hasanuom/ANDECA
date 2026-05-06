#!/usr/bin/env python3
"""Configure NDT TX harmonics at runtime and optionally verify via live packets.

This tool sends PAC_ID_TX_CONFIGURATION and PAC_ID_TX_ENABLE commands over the
existing packet protocol. It is intended to test whether the sensor firmware
accepts runtime frequency/amplitude/phase changes (without reflashing).

Examples:
    python3 configure_tx.py --port /dev/ttyUSB0 --baud 1000000 \
        --harmonic 1200:1.0:0.0 --harmonic 2400:0.6:0.0 --harmonic 3600:0.4:0.0

    python3 configure_tx.py --harmonic 1000:1.0:0.0 --no-verify
"""

from __future__ import annotations

import argparse
import math
import struct
import sys
import time
from typing import List, Tuple

from packet import Packet, PacketSerial, make_tx_config_payload
from pac_ids import (
    GET_MASK,
    SET_MASK,
    PAC_ID_ERROR,
    PAC_ID_HARMONICS_RX,
    PAC_ID_HARMONICS_TXI,
    PAC_ID_SETTINGS_STREAMING,
    PAC_ID_TX_CONFIGURATION,
    PAC_ID_TX_ENABLE,
)


def parse_harmonics_payload(data: bytes) -> List[dict]:
    """Decode TI DSP middle-endian interleaved complex harmonics."""
    n_floats = len(data) // 4
    bigendian = bytearray()
    for i in range(0, len(data), 4):
        lsword = data[i : i + 2]
        word = data[i + 2 : i + 4] + lsword
        bigendian += word

    floats = list(struct.unpack(f">{n_floats}f", bytes(bigendian)))
    out: List[dict] = []
    for i in range(0, len(floats), 2):
        real = floats[i]
        imag = floats[i + 1] if i + 1 < len(floats) else 0.0
        out.append({
            "real": real,
            "imag": imag,
            "mag": math.sqrt(real * real + imag * imag),
        })
    return out


def parse_harmonic_arg(value: str) -> Tuple[int, float, float]:
    """Parse one --harmonic FREQ:MAG:PHASE entry."""
    parts = value.split(":")
    if len(parts) != 3:
        raise argparse.ArgumentTypeError(
            "harmonic must look like FREQ:MAG:PHASE (example: 1200:1.0:0.0)"
        )

    try:
        freq = int(parts[0], 0)
        mag = float(parts[1])
        phase = float(parts[2])
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc

    if freq < 0 or freq > 0xFFFF:
        raise argparse.ArgumentTypeError("freq must fit uint16 (0..65535)")

    return (freq, mag, phase)


def read_for(link: PacketSerial, seconds: float, wanted_cmd: int | None) -> List[Packet]:
    """Collect packets for a fixed time window, optionally filtered by command."""
    deadline = time.time() + max(0.0, seconds)
    out: List[Packet] = []
    while time.time() < deadline:
        pkt = link.receive()
        if pkt is None:
            continue
        if wanted_cmd is not None and (pkt.command & ~GET_MASK) != wanted_cmd:
            continue
        out.append(pkt)
    return out


def maybe_print_error_packets(pkts: List[Packet]) -> None:
    for pkt in pkts:
        if (pkt.command & ~GET_MASK) == PAC_ID_ERROR:
            print(f"Sensor reported PAC_ID_ERROR payload={pkt.payload.hex()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send NDT TX configuration and verify with live harmonics packets."
    )
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial port")
    parser.add_argument("--baud", type=int, default=1000000, help="Serial baud")
    parser.add_argument(
        "--harmonic",
        dest="harmonics",
        action="append",
        type=parse_harmonic_arg,
        required=True,
        help="One entry per harmonic as FREQ:MAG:PHASE (repeat for multiple).",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="Global TX scale sent in PAC_ID_TX_CONFIGURATION",
    )
    parser.add_argument(
        "--enable-mask",
        type=lambda x: int(x, 0),
        default=None,
        help="Bitmask for enabled harmonics (default: lowest N bits for provided entries)",
    )
    parser.add_argument(
        "--tx-enable",
        type=int,
        choices=[0, 1],
        default=1,
        help="Send PAC_ID_TX_ENABLE with 0 or 1 after config",
    )
    parser.add_argument(
        "--stream-enable",
        type=int,
        default=4,
        help="Streaming mode byte for PAC_ID_SETTINGS_STREAMING while verifying",
    )
    parser.add_argument(
        "--watch",
        choices=["rx", "txi"],
        default="rx",
        help="During verification, watch HARMONICS_RX or HARMONICS_TXI packets",
    )
    parser.add_argument(
        "--verify-seconds",
        type=float,
        default=3.0,
        help="How long to watch harmonics after configuration",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Only send configuration packets and exit",
    )

    args = parser.parse_args()

    if args.enable_mask is None:
        enable_mask = (1 << len(args.harmonics)) - 1
    else:
        enable_mask = args.enable_mask

    print(f"Opening {args.port} @ {args.baud}...")
    try:
        link = PacketSerial(args.port, baudrate=args.baud, timeout=0.2)
    except Exception as exc:
        print(f"ERROR: cannot open serial port: {exc}", file=sys.stderr)
        sys.exit(1)

    seq = 1

    try:
        payload = make_tx_config_payload(enable_mask, args.scale, args.harmonics)
        cfg = Packet(
            device_address=0,
            command=SET_MASK | PAC_ID_TX_CONFIGURATION,
            seq_num=seq,
            payload=payload,
        )
        seq += 1
        link.send(cfg)
        print(
            "Sent TX config: "
            f"enable_mask=0x{enable_mask:04X}, scale={args.scale}, "
            f"harmonics={args.harmonics}"
        )

        tx_payload = struct.pack(">B", args.tx_enable)
        tx_en = Packet(
            device_address=0,
            command=SET_MASK | PAC_ID_TX_ENABLE,
            seq_num=seq,
            payload=tx_payload,
        )
        seq += 1
        link.send(tx_en)
        print(f"Sent TX enable: {args.tx_enable}")

        # Collect immediate asynchronous responses/errors if any.
        immediate = read_for(link, 0.5, wanted_cmd=None)
        maybe_print_error_packets(immediate)

        if args.no_verify:
            print("Configuration packets sent (verification disabled).")
            return

        stream_payload = struct.pack(">B", args.stream_enable)
        stream_on = Packet(
            device_address=0,
            command=SET_MASK | PAC_ID_SETTINGS_STREAMING,
            seq_num=seq,
            payload=stream_payload,
        )
        seq += 1
        link.send(stream_on)
        time.sleep(0.2)
        print(f"Streaming enabled with mode byte {args.stream_enable}.")

        watch_cmd = PAC_ID_HARMONICS_RX if args.watch == "rx" else PAC_ID_HARMONICS_TXI
        observed = 0
        sample_print_limit = 8
        print(f"Watching {args.watch.upper()} harmonics for {args.verify_seconds:.1f}s...")

        for pkt in read_for(link, args.verify_seconds, wanted_cmd=watch_cmd):
            observed += 1
            harmonics = parse_harmonics_payload(pkt.payload)
            mags = [h["mag"] for h in harmonics[: min(4, len(harmonics))]]
            if observed <= sample_print_limit:
                print(f"  pkt#{observed:03d} first mags: {mags}")

        if observed == 0:
            print("No harmonics packets observed during verification window.")
        else:
            print(f"Observed {observed} harmonics packets.")
            print("If magnitudes changed as expected, runtime TX config is active.")

    finally:
        try:
            off = Packet(
                device_address=0,
                command=SET_MASK | PAC_ID_SETTINGS_STREAMING,
                seq_num=seq,
                payload=struct.pack(">B", 0),
            )
            link.send(off)
        except Exception:
            pass
        try:
            link.ser.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
