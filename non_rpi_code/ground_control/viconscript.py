#!/usr/bin/env python3
"""
student_vicon_client_template.py

Purpose
-------
Template script showing how a third-party device or application can interface
with the Vicon Manager REST API.

This version sends Vicon position and orientation data to a Pixhawk drone
via MAVLink, allowing the drone to use Vicon as its primary localization source.

Workflow
--------
1. Start recording on the Vicon machine
2. Poll the latest live pose sample
3. Send position/orientation to drone via MAVLink VISION_POSITION_ESTIMATE
4. Use the sample in your own device/application logic
5. Stop recording when finished

Drone Configuration
-------------------
For the drone to use Vicon as primary localization:
- PX4: Set EKF2_AID_MASK to include vision position/attitude
- ArduPilot: Set AHRS_EKF_TYPE=3, VISION_POS_XY=1, etc.
- Ensure MAVLink connection matches MAVLINK_CONNECTION
- Coordinate frame: Vicon ENU converted to MAVLink NED

What this script expects
------------------------
- fast_api.exe running on the Vicon machine
- vicon_handler.exe running on the Vicon machine
- correct Bearer token
- network access to the API port

API routes used
---------------
POST /v1/start
GET  /v1/live/latest
POST /v1/stop
GET  /v1/status

Notes
-----
- This is a polling client, not a push-stream client
- The API returns the latest available sample, not every frame
- Rotation can be requested by setting include_rotation=True

Dependencies
------------
- pip install requests pymavlink
"""

from __future__ import annotations

import time
import uuid
from typing import Optional, Dict, Any
import math

import requests
from pymavlink import mavutil


# ---------------------------------------------------------------------
# CONFIG - STUDENTS SHOULD EDIT THESE
# ---------------------------------------------------------------------

API_BASE_URL = "http://192.168.10.1:8080"   # Vicon machine IP and API port
BEARER_TOKEN = "changeme"

TRIAL_NAME = "StudentTrial_001"
CAPTURE_DURATION_S: Optional[float] = None   # Set to a number for auto-stop, or None

INCLUDE_ROTATION = True
POLL_INTERVAL_S = 0.05   # 20 Hz polling example; adjust as needed

MAVLINK_CONNECTION = "udpout:127.0.0.1:14551"  # UDP from Mission Planner forwarding. Change port if needed.
MAVLINK_BAUD = 57600  # Only used for direct serial connection, ignored for UDP

mav = None  # Global MAVLink connection


def quaternion_to_euler(qw: float, qx: float, qy: float, qz: float) -> tuple[float, float, float]:
    """Convert quaternion (w, x, y, z) to roll, pitch, yaw in radians."""
    sinr_cosp = 2.0 * (qw * qx + qy * qz)
    cosr_cosp = 1.0 - 2.0 * (qx * qx + qy * qy)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    sinp = 2.0 * (qw * qy - qz * qx)
    if sinp >= 1.0:
        pitch = math.pi / 2.0
    elif sinp <= -1.0:
        pitch = -math.pi / 2.0
    else:
        pitch = math.asin(sinp)

    siny_cosp = 2.0 * (qw * qz + qx * qy)
    cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return roll, pitch, yaw

# ---------------------------------------------------------------------
# SMALL API CLIENT
# ---------------------------------------------------------------------

class ViconApiClient:
    def __init__(self, base_url: str, bearer_token: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        })

    def ping(self) -> Dict[str, Any]:
        url = f"{self.base_url}/v1/ping"
        r = self.session.get(url, timeout=2.0)
        r.raise_for_status()
        return r.json()

    def status(self) -> Dict[str, Any]:
        url = f"{self.base_url}/v1/status"
        r = self.session.get(url, timeout=2.0)
        r.raise_for_status()
        return r.json()

    def start(self, trial_name: str, duration: Optional[float] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/v1/start"
        payload = {
            "trial_name": trial_name,
            "duration": duration,
            "command_id": f"start-{uuid.uuid4()}",
        }
        r = self.session.post(url, json=payload, timeout=3.0)
        r.raise_for_status()
        return r.json()

    def stop(self, reason: str = "") -> Dict[str, Any]:
        url = f"{self.base_url}/v1/stop"
        payload = {
            "reason": reason,
            "command_id": f"stop-{uuid.uuid4()}",
        }
        r = self.session.post(url, json=payload, timeout=3.0)
        r.raise_for_status()
        return r.json()

    def live_latest(self, include_rotation: bool = False) -> Dict[str, Any]:
        url = f"{self.base_url}/v1/live/latest"
        params = {"include_rotation": str(include_rotation).lower()}
        r = self.session.get(url, params=params, timeout=2.0)
        r.raise_for_status()
        return r.json()


# ---------------------------------------------------------------------
# STUDENT HOOK: PUT YOUR OWN DEVICE LOGIC HERE
# ---------------------------------------------------------------------

def handle_live_sample(sample: Dict[str, Any]) -> None:
    """
    Replace this with your own logic.

    For example, a student might:
    - display the position on screen
    - send it to another device
    - use it to move a game object
    - save selected fields to their own log
    """
    global mav

    frame = sample.get("frame")
    tx_mm = sample.get("tx_mm", 0)
    ty_mm = sample.get("ty_mm", 0)
    tz_mm = sample.get("tz_mm", 0)

    # Convert mm to meters and ENU to NED coordinate frame
    x_ned = ty_mm / 1000.0
    y_ned = tx_mm / 1000.0
    z_ned = -tz_mm / 1000.0

    qw = sample.get("qw", 1.0)
    qx = sample.get("qx", 0.0)
    qy = sample.get("qy", 0.0)
    qz = sample.get("qz", 0.0)
    roll, pitch, yaw = quaternion_to_euler(qw, qx, qy, qz)
    usec = int(time.time() * 1e6)

    # Send to drone via MAVLink VISION_POSITION_ESTIMATE
    if mav:
        mav.mav.vision_position_estimate_send(usec, x_ned, y_ned, z_ned, roll, pitch, yaw)

    message = f"frame={frame}  pos_ned_m=({x_ned:.2f}, {y_ned:.2f}, {z_ned:.2f})"

    if "qw" in sample:
        message += f"  quat=({qw:.4f}, {qx:.4f}, {qy:.4f}, {qz:.4f})"
        message += f"  rpy_rad=({roll:.4f}, {pitch:.4f}, {yaw:.4f})"
    print(message)


# ---------------------------------------------------------------------
# MAIN EXAMPLE WORKFLOW
# ---------------------------------------------------------------------

def main():
    client = ViconApiClient(API_BASE_URL, BEARER_TOKEN)
    global mav
    mav = mavutil.mavlink_connection(MAVLINK_CONNECTION, baud=MAVLINK_BAUD)

    print("Checking API connection...")
    try:
        print(client.ping())
    except Exception as e:
        print(f"Failed to reach API: {e}")
        return

    print("\nInitial status:")
    try:
        print(client.status())
    except Exception as e:
        print(f"Failed to read status: {e}")
        return

    print("\nSending START...")
    try:
        start_resp = client.start(TRIAL_NAME, CAPTURE_DURATION_S)
        print(start_resp)
    except Exception as e:
        print(f"Failed to start recording: {e}")
        return

    print("\nPolling live samples... (Press Ctrl+C to stop)")
    samples_received = 0

    try:
        while True:
            try:
                resp = client.live_latest(include_rotation=INCLUDE_ROTATION)
            except Exception as e:
                print(f"Live poll failed: {e}")
                time.sleep(POLL_INTERVAL_S)
                continue

            sample = resp.get("sample")
            active = resp.get("active", False)

            if sample is not None:
                handle_live_sample(sample)
                samples_received += 1
            else:
                if active:
                    print("Capture active, but no live sample available yet.")
                else:
                    print("Capture is not active.")

            time.sleep(POLL_INTERVAL_S)

    except KeyboardInterrupt:
        print("\nInterrupted by user (Ctrl+C)")

    finally:
        print("\nSending STOP...")
        try:
            stop_resp = client.stop(reason="Student template finished")
            print(stop_resp)
        except Exception as e:
            print(f"Failed to stop recording: {e}")

    print(f"\nDone. Samples received: {samples_received}")

    print("\nFinal status:")
    try:
        print(client.status())
    except Exception as e:
        print(f"Failed to read final status: {e}")


if __name__ == "__main__":
    main()