"""Python equivalent of the C packet handling code.

This module defines a Packet class that mirrors the structure used by the
existing C implementation.  It provides helpers for checksum generation,
serialization/deserialization and a simple wrapper around a serial port.
"""

from __future__ import annotations
import struct
from typing import Optional, List

# Constants copied from the C code
PAC_HEADER = bytes([0xDE, 0x7E, 0xC7, 0xED])
PAC_PAYLOAD_NBYTES_MAX = 128  # adjust to the value in packet.h if different


def _checksum(data: bytes) -> int:
    """Compute 16‑bit two's‑complement checksum, same as pac_checksum_calc."""
    # sum over 16‑bit words
    if len(data) % 2:
        data += b"\x00"
    s = 0
    for hi, lo in zip(data[0::2], data[1::2]):
        s += (hi << 8) | lo
    s &= 0xFFFF
    s = (~s + 1) & 0xFFFF
    return s


class Packet:
    def __init__(
        self,
        device_address: int = 0,
        command: int = 0,
        seq_num: int = 0,
        payload: Optional[bytes] = None,
        use_checksum: bool = True,
    ) -> None:
        self.device_address = device_address
        self.command = command
        self.seq_num = seq_num
        self.payload = payload or b""
        self.use_checksum = use_checksum

    @property
    def nbytes_payload(self) -> int:
        return len(self.payload)

    def to_bytes(self) -> bytes:
        """Serialize a packet to a bytes object suitable for writing to a serial port."""
        if self.nbytes_payload > PAC_PAYLOAD_NBYTES_MAX:
            raise ValueError("payload too large")
        # header is two 16‑bit words big endian
        parts: List[bytes] = [PAC_HEADER]
        parts.append(struct.pack(">H", self.device_address))
        parts.append(struct.pack(">H", self.command))
        parts.append(struct.pack(">H", self.seq_num))
        parts.append(struct.pack(">H", self.nbytes_payload))
        if self.payload:
            parts.append(self.payload)
        if self.use_checksum:
            chk = _checksum(b"".join(parts[1:]))  # exclude header from checksum?
            parts.append(struct.pack(">H", chk))
        return b"".join(parts)

    @classmethod
    def from_bytes(cls, data: bytes) -> "Packet":
        """Parse a packet from bytes received from the wire.  Raises ValueError
        if the header is wrong or checksum mismatch."""
        if len(data) < 12:
            raise ValueError("packet too short")
        if data[0:4] != PAC_HEADER:
            raise ValueError("bad header")
        # read fixed fields
        device_address, command, seq_num, nbytes_payload = struct.unpack(
            ">HHHH", data[4:12]
        )
        expected_len = 4 + 8 + nbytes_payload + (2 if len(data) >= 14 else 0)
        if len(data) < expected_len:
            raise ValueError("incomplete packet")
        payload = data[12 : 12 + nbytes_payload]
        pkt = cls(
            device_address=device_address,
            command=command,
            seq_num=seq_num,
            payload=payload,
        )
        if len(data) >= 14 + nbytes_payload:
            recv_chk, = struct.unpack(">H", data[12 + nbytes_payload : 14 + nbytes_payload])
            calc_chk = _checksum(data[4 : 12 + nbytes_payload])
            if recv_chk != calc_chk:
                raise ValueError("checksum mismatch")
        return pkt


# helper to wrap serial communication
import serial

class PacketSerial:
    def __init__(self, port: str, baudrate: int = 1000000, timeout: float = 1.0) -> None:
        self.ser = serial.Serial(port, baudrate, timeout=timeout)

    def send(self, pkt: Packet) -> None:
        self.ser.write(pkt.to_bytes())

    def receive(self) -> Optional[Packet]:
        # read header first; resynchronize if we read mid-stream by
        # scanning for the 4-byte PAC_HEADER sequence.
        hdr = self.ser.read(4)
        if len(hdr) < 4:
            return None
        if hdr != PAC_HEADER:
            # slide window until we find the header or timeout
            buf = bytearray(hdr)
            while True:
                b = self.ser.read(1)
                if not b:
                    # timeout / no more data
                    return None
                buf.pop(0)
                buf.append(b[0])
                if bytes(buf) == PAC_HEADER:
                    hdr = bytes(buf)
                    break
        # read fixed fields
        rest = self.ser.read(8)
        if len(rest) < 8:
            return None
        device_address, command, seq_num, nbytes_payload = struct.unpack(
            ">HHHH", rest
        )
        payload = self.ser.read(nbytes_payload)
        if len(payload) < nbytes_payload:
            return None
        chk_bytes = self.ser.read(2)
        packet_bytes = hdr + rest + payload + chk_bytes
        return Packet.from_bytes(packet_bytes)


# example payload functions that mimic the C helper routines for tx config

def make_tx_config_payload(enable_mask: int, scale: float, harmonics: List[tuple]) -> bytes:
    """Construct the payload used in pac_tx_config_generate."""
    buf = bytearray()
    buf += struct.pack(">H", enable_mask)
    buf += struct.pack(">f", scale)  # default is little‑endian; use >f if big‑endian
    for freq, mag, phase in harmonics:
        # freq: uint16, mag: float, phase: float (big endian as in C code)
        buf += struct.pack(">Hff", freq, mag, phase)
    return bytes(buf)
