#!/usr/bin/env python3
"""
student_vicon_client_template.py

Purpose
-------
Template script showing how a third-party device or application can interface
with the Vicon Manager REST API.

Workflow
--------
1. Start recording on the Vicon machine
2. Poll the latest live pose sample
3. Use the sample in your own device/application logic
4. Stop recording when finished

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
"""

from __future__ import annotations

import time
import uuid
from typing import Optional, Dict, Any

import requests


# ---------------------------------------------------------------------
# CONFIG - STUDENTS SHOULD EDIT THESE
# ---------------------------------------------------------------------

API_BASE_URL = "http://192.168.10.1:8080"   # Vicon machine IP and API port
BEARER_TOKEN = "changeme"

TRIAL_NAME = "StudentTrial_001"
CAPTURE_DURATION_S: Optional[float] = None   # Set to a number for auto-stop, or None

INCLUDE_ROTATION = True
POLL_INTERVAL_S = 0.05   # 20 Hz polling example; adjust as needed
RUN_FOR_S = 10.0         # How long this example polls before stopping


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
    frame = sample.get("frame")
    tx = sample.get("tx_mm")
    ty = sample.get("ty_mm")
    tz = sample.get("tz_mm")

    message = f"frame={frame}  pos_mm=({tx:.2f}, {ty:.2f}, {tz:.2f})"

    if "qw" in sample:
        qw = sample.get("qw")
        qx = sample.get("qx")
        qy = sample.get("qy")
        qz = sample.get("qz")
        message += f"  quat=({qw:.4f}, {qx:.4f}, {qy:.4f}, {qz:.4f})"

    print(message)


# ---------------------------------------------------------------------
# MAIN EXAMPLE WORKFLOW
# ---------------------------------------------------------------------

def main():
    client = ViconApiClient(API_BASE_URL, BEARER_TOKEN)

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

    print("\nPolling live samples...")
    t0 = time.time()
    samples_received = 0

    try:
        while (time.time() - t0) < RUN_FOR_S:
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