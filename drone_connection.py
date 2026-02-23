from pymavlink import mavutil
import time

connection_string = '/dev/ttyAMA0' 
baud_rate = 57600  # Default for Telem ports; USB is usually 115200

print(f"Connecting to Pixhawk on {connection_string}...")

# 2. Establish connection
# autoreconnect=True helps if the cable is loose
master = mavutil.mavlink_connection(connection_string, baud=baud_rate)

# 3. Wait for the first heartbeat 
# This confirms the Pixhawk is actually talking back
print("Waiting for heartbeat...")
master.wait_heartbeat()

print(f"Heartbeat received from system (ID {master.target_system}) component (ID {master.target_component})")

# 4. Simple loop to monitor the connection
try:
    while True:
        # Check for any incoming messages
        msg = master.recv_match(blocking=True, timeout=1.0)
        if msg:
            if msg.get_type() == 'HEARTBEAT':
                print("Link is alive...")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("Closing connection.")