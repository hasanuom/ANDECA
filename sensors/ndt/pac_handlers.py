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
        # TI DSP middle-endian format: each float is two 16-bit words with
        # word order reversed. Swap the 16-bit words then unpack as big-endian floats.
        data = pkt.payload
        n_samples = len(data) // 4
        bigendian = bytearray(0)
        for i in range(0, len(data), 4):
            lsword = data[i : i + 2]
            word = data[i + 2 : i + 4] + lsword
            bigendian += word
        floats = list(struct.unpack(f">{n_samples}f", bytes(bigendian)))
        return floats

    # harmonics packets: real/imag pairs as interleaved floats
    if cmd in (
        ids.PAC_ID_HARMONICS_CAL_OP,
        ids.PAC_ID_HARMONICS_TRANS,
        ids.PAC_ID_HARMONICS_RX,
        ids.PAC_ID_HARMONICS_TXI,
    ):
        # TI DSP middle-endian format: each float is two 16-bit words with
        # word order reversed. Swap the 16-bit words then unpack as big-endian floats.
        data = pkt.payload
        n_floats = len(data) // 4
        bigendian = bytearray(0)
        for i in range(0, len(data), 4):
            lsword = data[i : i + 2]
            word = data[i + 2 : i + 4] + lsword
            bigendian += word
        floats = list(struct.unpack(f">{n_floats}f", bytes(bigendian)))
        
        # Pair into (real, imag) complex tuples
        harmonics = []
        for i in range(0, len(floats), 2):
            real = floats[i]
            imag = floats[i + 1] if i + 1 < len(floats) else 0.0
            harmonics.append((real, imag))
        return harmonics

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
