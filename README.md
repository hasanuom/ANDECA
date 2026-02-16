# ANDECA
Codebase for EEE MEng Project (Group 9)

This repository contains the flight control and mission logic for the ANDECA drone, running on a Raspberry Pi 5 interfaced with a Pixhawk 6C.

## Setup & Installation

Follow these steps to set up the development environment on a fresh Raspberry Pi OS installation.

### 1. System Dependencies
The Pi must be configured for UART communication and requires specific build tools for MAVLink.

```bash
# Update system and install Python headers/tools
sudo apt update && sudo apt upgrade -y
sudo apt install python3-dev python3-pip python3-venv libxml2-dev libxslt-dev -y

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
