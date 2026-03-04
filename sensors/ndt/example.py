"""Query firmware version.
"""

from packet import Packet, PacketSerial
import pac_ids as ids
import time


def main():
    link = PacketSerial("/dev/ttyUSB0", baudrate=1000000, timeout=0.5)
    # Send GET for firmware version and then scan incoming packets for up to
    # 3 seconds looking specifically for a firmware reply.
    pkt = Packet(device_address=0, command=ids.GET_MASK | ids.PAC_ID_FW_VERS, seq_num=1)
    print("Querying firmware version")
    link.send(pkt)

    deadline = time.time() + 3.0
    found = False
    while time.time() < deadline:
        resp = link.receive()
        if resp is None:
            continue
        # If this packet is the firmware response (strip GET/SET mask for safety)
        if (resp.command & ~ids.GET_MASK) == ids.PAC_ID_FW_VERS:
            try:
                s = resp.payload.decode("ascii", errors="replace").strip()
            except Exception as e:
                s = f"<decode error: {e}>"
            print(f"Firmware version: {s}")
            found = True
            break

    if not found:
        print("Firmware reply not seen within timeout (3s). Device may be streaming or not support PAC_ID_FW_VERS.)")


if __name__ == "__main__":
    main()
