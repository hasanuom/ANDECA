# ANDECA
Codebase for EEE MEng Project (Group 9)

This repository contains the flight control and mission logic for the ANDECA drone, running on a Raspberry Pi 5 interfaced with a Pixhawk 6C.

## Setup & Installation

Follow these steps to set up the development environment on a fresh Raspberry Pi OS installation.

### (Recommendation)
Expand filesystem 

- Open the terminal and type:
`sudo raspi-config`

- Use the arrow keys to select 6 Advanced Options.

- Select A1 Expand Filesystem.

- Hit Enter. You should see a message saying the partition will be resized upon reboot.

- Select Finish and agree to Reboot.

To make sure you aren't still cramped into a tiny partition, run
`df -h`
Look at the entry for /dev/root (or sometimes just /). You should see plenty of "Avail" space.

### 1. System Dependencies
The Pi must be configured for UART communication and requires specific build tools for MAVLink.

```bash
# Update system and install Python headers/tools
sudo apt update && sudo apt upgrade -y
sudo apt install python3-dev python3-pip python3-venv libxml2-dev libxslt-dev swig liblgpio-dev -y

# Remove ModemManager to prevent serial port interference
sudo apt purge modemmanager -y
```


### 2. Hardware Configuration

The Pi 5 serial pins must be released from the system console to allow the Pixhawk to communicate.

- Run `sudo raspi-config`

- Navigate to Interface Options > Serial Port.

- Select No for the login shell.

- Select Yes for the serial port hardware.

- Finish and reboot the Pi.

- Add your user to the dialout group: `sudo usermod -a -G dialout $USER`


### 3. Environment Setup

Always use the virtual environment to avoid "externally-managed-environment" errors.

Clone the repository
```bash
mkdir -p ~/Code && cd ~/Code
git clone https://github.com/hasanuom/ANDECA
cd ANDECA
```

Create and activate virtual environment
```bash
python3 -m venv drone_env
source drone_env/bin/activate
```
```bash
# Install requirements
pip install --upgrade pip
pip install -r requirements.txt
```


### 4. Connection & Testing

To verify the link between the Pi and the Pixhawk, ensure the drone_env is active and run:
```bash
# Connect via MAVProxy
mavproxy.py --master=/dev/ttyAMA0
```


## 🔌 Hardware Wiring (Pi 5 to Pixhawk 6C)

| Raspberry Pi 5 Pin | Function | Pixhawk 6C (Telem2) |
| :--- | :--- | :--- |
| **Any Ground Pin** | GND | GND (Pin 6)|
| **Pin 8** | TX | RX (Pin 3) |
| **Pin 10** | RX | TX (Pin 2) |

## Other things

### To set the Pi to Read-only Mode

1) Open your terminal and type: sudo raspi-config

2) Navigate to Performance Options → Overlay File System.

3) Select Yes to enable the overlay.

4) Select Yes to write-protect the boot partition.

5) Reboot.

### Git

Set details
```
git config --global user.email "you@example.com"
git config --global user.name "Your Name"
```
Persist details (stores in plain text so not really safe)
```
git config --global credential.helper store
```

### DATED - NOT DOING ANYMORE:
## Headless Pi Networking Guide (University/eduroam)

This guide outlines how to provide internet to a Raspberry Pi via a Windows laptop connected to a restricted network (like eduroam).
### 1. Windows Configuration 

The laptop acts as the router. We use Internet Connection Sharing (ICS) to hide the Pi's MAC address from the university firewall.

Disable the Firewall: If connection fails, temporarily disable the Windows Firewall or ensure "Network Discovery" is on.

Enable ICS:

- Open Network Connections (ncpa.cpl).

- Right-click Wi-Fi > Properties > Sharing tab.

- Check: “Allow other network users to connect...”.

- Select your Pi's adapter (e.g., Ethernet 2) in the dropdown (if it's there).

- Reset ICS (The "Flicker"): If the Pi has no internet after a reboot, uncheck and re-check the Sharing box to restart the Windows DHCP service.

### 2. Raspberry Pi Configuration 

Since Debian Trixie uses NetworkManager, we use nmcli to manage connections.

Identity Reset:
```bash
sudo nmcli connection modify "Wired connection 1" ethernet.cloned-mac-address ""
```
IP Configuration: Set the connection to automatic (DHCP). Windows ICS will assign the Pi an IP in the 192.168.137.x range.
```bash
sudo nmcli connection modify "Wired connection 1" ipv4.method auto
```
Activate Changes:
```bash
sudo nmcli connection up "Wired connection 1"
```
Verification:

- Run `ip addr show eth0`. You should see an inet address (usually 192.168.137.xxx).

- Run `ping 8.8.8.8` If you get a response, the tunnel is working.

### IMPORTANT NOTE
On every reboot of the Pi you may need to run `sudo nmcli device reapply eth0`
