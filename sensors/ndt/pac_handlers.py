"""Utility routines to interpret packet payloads for display.

The C firmware has many "generate" and "parse" routines; this module
provides the minimal subset needed by the test script.  For packets that
contain time‑domain or spectrum samples the helper will convert the raw
bytes into a Python list of floats.
"""

import struct
from typing import Any, List
from packet import Packet
import pac_ids as ids


def parse_packet(pkt: Packet) -> Any:
    """Return a high‑level representation of the packet payload."""
    cmd = pkt.command & ~ids.GET_MASK  # strip off the GET/SET bit for comparison

    if pkt.command & ids.GET_MASK and cmd == ids.PAC_ID_FW_VERS:
        # firmware version is ASCII text terminated by \n
        return pkt.payload.decode("ascii", errors="ignore").strip()

    if cmd in (
        ids.PAC_ID_TIME_DOMAIN_RX,
        ids.PAC_ID_TIME_DOMAIN_TXI,
        ids.PAC_ID_TIME_DOMAIN_NULL,
        ids.PAC_ID_TIME_DOMAIN_TX,
        ids.PAC_ID_SPECTRUM_RX,
        ids.PAC_ID_SPECTRUM_TXI,
    ):
        # payload is a sequence of big‑endian float32 values
        floats: List[float] = []
        for i in range(0, len(pkt.payload), 4):
            chunk = pkt.payload[i : i + 4]
            if len(chunk) < 4:
                break
            floats.append(struct.unpack(">f", chunk)[0])
        return floats

    # settings packets consist of integer fields; return raw list of words
    if cmd == ids.PAC_ID_SETTINGS:
        words = []
        for i in range(0, len(pkt.payload), 2):
            if i + 1 < len(pkt.payload):
                words.append(struct.unpack(">H", pkt.payload[i : i + 2])[0])
        return words

    # fall‑back: return raw bytes in hex
    return pkt.payload.hex()


def summary(packet_data: Any) -> str:
    """Produce a human‑readable summary of the interpreted payload."""
    if isinstance(packet_data, str):
        return packet_data
    if isinstance(packet_data, list) and packet_data and isinstance(packet_data[0], float):
        vals = packet_data
        return (
            f"{len(vals)} samples; min={min(vals):.3f} max={max(vals):.3f} "
            f"mean={sum(vals)/len(vals):.3f}"
        )
    if isinstance(packet_data, list):
        return ",".join(str(x) for x in packet_data)
    return str(packet_data)
