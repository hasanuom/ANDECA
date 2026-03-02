"""Example showing how to send/receive packets over serial using packet.py."""

from packet import Packet, PacketSerial, make_tx_config_payload


def main():
    # open the serial port on the Pi (e.g. /dev/ttyS0 or /dev/serial0)
    link = PacketSerial("/dev/ttyUSB0", baudrate=1000000, timeout=0.5)

    # create a TX configuration packet
    harmonics = [ (1000, 0.5, 0.0), (2000, 0.25, 1.57) ]
    payload = make_tx_config_payload(enable_mask=0x0001, scale=0.75, harmonics=harmonics)
    pkt = Packet(device_address=1, command=0x10, seq_num=1, payload=payload)

    print("sending", pkt)
    link.send(pkt)

    # wait for a reply
    resp = link.receive()
    if resp:
        print("received reply", resp)
        # further parsing of resp.payload as needed


if __name__ == "__main__":
    main()
