#!/usr/bin/env python3
"""Drone Location Simulator
===========================
Simulates a Pixhawk 6C broadcasting MAVLink messages over TCP so that
ndt_heatmap.py can be developed and tested without physical hardware.

The simulated drone flies a lawnmower survey pattern (parallel lines at a
fixed altitude, stepping across in Y after each pass).  Position is sent as
MAVLink LOCAL_POSITION_NED, which is the same message format the real
Pixhawk streams during flight.

Usage:
    1.  python3 sim_drone.py          (start the simulator — it streams over UDP)
    2.  python3 ndt_heatmap.py        (connect with MAVLINK_CONNECTION = 'udpin:0.0.0.0:14550')

The simulator must be started BEFORE ndt_heatmap.py.
"""

import sys
import time
import math
from pymavlink import mavutil


# ============================================================
# SIMULATION CONSTANTS — adjust to match your intended flight plan
# ============================================================

# UDP destination port for the simulator stream.
# ndt_heatmap.py should have: MAVLINK_CONNECTION = 'udpin:0.0.0.0:14550'
SIM_UDP_PORT = 14550

# Lawnmower pattern dimensions (metres, from home position)
PATTERN_WIDTH  = 2.0   # extent along X (North)
PATTERN_HEIGHT = 10.0   # total extent along Y (East) to cover
LINE_SPACING   = 1.0    # distance between adjacent parallel lines (Y step)

# Drone speed along each line (m/s)
CRUISE_SPEED = 0.5

# Fixed flight altitude above home (metres).
# LOCAL_POSITION_NED z-axis is positive-down, so this becomes negative.
FLIGHT_ALTITUDE = 5.0

# Rate at which HEARTBEAT messages are broadcast (Hz)
HEARTBEAT_RATE = 1.0

# Rate at which LOCAL_POSITION_NED messages are broadcast (Hz)
POSITION_RATE = 10.0

# ============================================================


def _lawnmower_position(elapsed: float) -> tuple:
    """Return the simulated (x, y) position in metres at time *elapsed*
    seconds since the start of the survey.

    The pattern is:
        Line 0  x: 0 → WIDTH   at y = 0 * LINE_SPACING
        Line 1  x: WIDTH → 0   at y = 1 * LINE_SPACING
        Line 2  x: 0 → WIDTH   at y = 2 * LINE_SPACING
        ...
    After the last line the pattern wraps so testing can continue indefinitely.
    """
    line_duration = PATTERN_WIDTH / CRUISE_SPEED
    n_lines = max(1, int(PATTERN_HEIGHT / LINE_SPACING))
    total_duration = n_lines * line_duration

    # Wrap time so the pattern repeats
    t = elapsed % total_duration

    line_idx = int(t / line_duration)
    t_in_line = t - line_idx * line_duration
    progress = t_in_line / line_duration  # 0.0 → 1.0 along the current line

    y = min(line_idx * LINE_SPACING, PATTERN_HEIGHT)

    if line_idx % 2 == 0:
        x = progress * PATTERN_WIDTH          # left → right
    else:
        x = PATTERN_WIDTH * (1.0 - progress)  # right → left

    return x, y


def main() -> None:
    connection_str = f'udpout:127.0.0.1:{SIM_UDP_PORT}'

    print("=" * 60)
    print("NDT Drone Location Simulator")
    print("=" * 60)
    print(f"Lawnmower pattern  : {PATTERN_WIDTH} m wide  x  {PATTERN_HEIGHT} m tall")
    print(f"Line spacing       : {LINE_SPACING} m")
    print(f"Cruise speed       : {CRUISE_SPEED} m/s")
    print(f"Flight altitude    : {FLIGHT_ALTITUDE} m")
    print(f"MAVLink UDP port   : {SIM_UDP_PORT}")
    print()
    print(f"Streaming MAVLink UDP packets to 127.0.0.1:{SIM_UDP_PORT}")
    print("(Start sim_drone.py first, then run ndt_heatmap.py)")
    print()

    try:
        mav = mavutil.mavlink_connection(
            connection_str,
            source_system=1,
            source_component=1,
        )
    except Exception as exc:
        print(f"ERROR: Failed to open connection: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Broadcasting heartbeat + LOCAL_POSITION_NED ...")
    print("Press Ctrl+C to stop.\n")

    sim_start = time.time()
    last_heartbeat = 0.0
    last_position = 0.0
    hb_interval = 1.0 / HEARTBEAT_RATE
    pos_interval = 1.0 / POSITION_RATE

    try:
        while True:
            now = time.time()
            elapsed = now - sim_start
            boot_ms = int(elapsed * 1000)

            # ── HEARTBEAT ────────────────────────────────────────────────────
            if now - last_heartbeat >= hb_interval:
                mav.mav.heartbeat_send(
                    mavutil.mavlink.MAV_TYPE_QUADROTOR,
                    mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
                    mavutil.mavlink.MAV_MODE_FLAG_AUTO_ENABLED,
                    0,
                    mavutil.mavlink.MAV_STATE_ACTIVE,
                )
                last_heartbeat = now

            # ── LOCAL_POSITION_NED ───────────────────────────────────────────
            if now - last_position >= pos_interval:
                x, y = _lawnmower_position(elapsed)
                z = -FLIGHT_ALTITUDE  # NED convention: up is negative z

                mav.mav.local_position_ned_send(
                    boot_ms,  # time_boot_ms
                    x,        # x  North (m)
                    y,        # y  East  (m)
                    z,        # z  Down  (m) — negative means above home
                    0.0,      # vx
                    0.0,      # vy
                    0.0,      # vz
                )

                n_lines = max(1, int(PATTERN_HEIGHT / LINE_SPACING))
                current_line = int(elapsed / (PATTERN_WIDTH / CRUISE_SPEED)) % n_lines
                print(
                    f"\r[{elapsed:8.2f} s]  "
                    f"x = {x:6.2f} m   y = {y:6.2f} m   z = {z:6.2f} m   "
                    f"(line {current_line} / {n_lines - 1})",
                    end='', flush=True,
                )
                last_position = now

            time.sleep(0.005)  # ~200 Hz loop; actual send rates governed by intervals above

    except KeyboardInterrupt:
        print("\n\nSimulator stopped.")


if __name__ == '__main__':
    main()
