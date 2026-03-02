"""Live monitor for NDT sensor: configure (optional) and print per-second summaries.

Example:
  python3 monitor_live.py /dev/ttyUSB0 --baud 1000000 --freq 1000
"""
from __future__ import annotations
import time
import argparse
import math
from typing import List, Tuple, Optional

from packet import PacketSerial, Packet, make_tx_config_payload
from pac_handlers import parse_packet
import pac_ids as ids


def configure_sensor(link: PacketSerial, seq: int, freq: Optional[int], enable_mask: int = 0x0001, scale: float = 1.0) -> int:
    if freq is None:
        return seq
    harmonics: List[Tuple[int, float, float]] = [(int(freq), 1.0, 0.0)]
    payload = make_tx_config_payload(enable_mask, scale, harmonics)
    pkt = Packet(device_address=ids.DEFAULT_DEVICE_ADDRESS, command=ids.PAC_ID_TX_CONFIGURATION | ids.SET_MASK, seq_num=seq, payload=payload)
    link.send(pkt)
    # try to clear any immediate response
    _ = link.receive()
    return seq + 1


def rms(values: List[float]) -> float:
    if not values:
        return 0.0
    return math.sqrt(sum(x * x for x in values) / len(values))


def monitor(loop_port: str, baud: int, freq: Optional[int], timeout: float, poll_interval: Optional[float] = None, poll_cmd: str = "time", baseline_seconds: int = 0, alert_mult: Optional[float] = None) -> None:
    link = PacketSerial(loop_port, baudrate=baud, timeout=timeout)
    seq = 1
    seq = configure_sensor(link, seq, freq)
    last_poll = 0.0

    print(f"listening {loop_port} @ {baud}, ctrl-C to stop")
    try:
        # baseline collection for alerting
        baseline_rms: List[float] = []

        while True:
            window_start = time.time()
            packets = 0
            sample_packets = 0
            samples_total = 0
            rms_list: List[float] = []
            non_sample = 0
            # send a GET request at the start of the second if polling is enabled
            now = time.time()
            if poll_interval is not None and (now - last_poll) >= poll_interval:
                cmd = ids.PAC_ID_TIME_DOMAIN_RX if poll_cmd == "time" else ids.PAC_ID_SPECTRUM_RX
                get_pkt = Packet(device_address=ids.DEFAULT_DEVICE_ADDRESS, command=cmd | ids.GET_MASK, seq_num=seq)
                seq += 1
                link.send(get_pkt)
                last_poll = now

            # collect for one second
            while time.time() - window_start < 1.0:
                pkt = link.receive()
                if pkt is None:
                    continue
                packets += 1
                parsed = parse_packet(pkt)
                if isinstance(parsed, list) and parsed and isinstance(parsed[0], float):
                    sample_packets += 1
                    samples_total += len(parsed)
                    r = rms(parsed)
                    if math.isfinite(r):
                        rms_list.append(r)
                else:
                    non_sample += 1

            # compute summary
            mean_rms = sum(rms_list) / len(rms_list) if rms_list else 0.0
            max_rms = max(rms_list) if rms_list else 0.0

            # baseline collection
            if baseline_seconds and len(baseline_rms) < baseline_seconds:
                baseline_rms.append(mean_rms)
                print(
                    f"{time.strftime('%H:%M:%S')} pkts={packets} samples_pkts={sample_packets} samples={samples_total} "
                    f"non_sample={non_sample} mean_rms={mean_rms:.6g} max_rms={max_rms:.6g} (baseline {len(baseline_rms)}/{baseline_seconds})"
                )
                continue

            # check alert against baseline
            alert = False
            if alert_mult is not None and baseline_rms:
                bmean = sum(baseline_rms) / len(baseline_rms)
                bstd = math.sqrt(sum((x - bmean) ** 2 for x in baseline_rms) / len(baseline_rms))
                if mean_rms > bmean + alert_mult * bstd:
                    alert = True

            if alert:
                print(f"{time.strftime('%H:%M:%S')} pkts={packets} samples_pkts={sample_packets} samples={samples_total} "
                      f"non_sample={non_sample} mean_rms={mean_rms:.6g} max_rms={max_rms:.6g} ALERT!")
            else:
                print(
                    f"{time.strftime('%H:%M:%S')} pkts={packets} samples_pkts={sample_packets} samples={samples_total} "
                    f"non_sample={non_sample} mean_rms={mean_rms:.6g} max_rms={max_rms:.6g}"
                )
    except KeyboardInterrupt:
        print("stopped")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("port")
    p.add_argument("--baud", type=int, default=1000000)
    p.add_argument("--freq", type=float, default=None, help="single harmonic frequency to configure (Hz)")
    p.add_argument("--timeout", type=float, default=0.2)
    p.add_argument("--poll-interval", type=float, default=None, help="send GET every N seconds (enables polling)")
    p.add_argument("--poll-cmd", choices=["time", "spectrum"], default="time", help="which GET to send when polling")
    p.add_argument("--baseline-secs", type=int, default=0, help="collect baseline RMS for N seconds before alerting")
    p.add_argument("--alert-mult", type=float, default=None, help="alert when RMS > baseline_mean + alert_mult*baseline_std")
    args = p.parse_args()
    monitor(args.port, args.baud, args.freq, args.timeout, args.poll_interval, args.poll_cmd, args.baseline_secs, args.alert_mult)


if __name__ == "__main__":
    main()
