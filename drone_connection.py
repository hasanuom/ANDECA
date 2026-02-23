import time
import board
import adafruit_vl53l4cd
from pymavlink import mavutil

# --- 1. INITIALIZE SENSOR ---
i2c = board.I2C()
vl53 = adafruit_vl53l4cd.VL53L4CD(i2c)
vl53.inter_measurement = 0
vl53.timing_budget = 50
vl53.start_ranging()

# --- 2. INITIALIZE MAVLINK ---
# Change to '/dev/ttyACM0' if using a USB cable
connection_string = '/dev/ttyAMA0' 
master = mavutil.mavlink_connection(connection_string, baud=57600)
print("Waiting for Pixhawk heartbeat...")
master.wait_heartbeat()
print("Heartbeat received! Sending laser data...")

def send_distance_message(dist_cm):
    """
    Sends the DISTANCE_SENSOR message to ArduPilot.
    dist_cm: distance in centimeters
    """
    # MAVLink uses millimeters for distance
    dist_mm = int(dist_cm * 10)
    
    master.mav.distance_sensor_send(
        0,          # time_boot_ms (ignored if 0)
        10,         # min_distance (cm)
        130,        # max_distance (cm) - VL53L4CD max is ~1.3m
        dist_mm,    # current_distance (mm)
        0,          # type (0 = Laser)
        1,          # id (sensor ID)
        mavutil.mavlink.MAV_SENSOR_ROTATION_PITCH_270, # orientation (facing down)
        0           # covariance
    )

try:
    while True:
        if vl53.data_ready:
            distance = vl53.distance
            print(f"Distance: {distance:.2f} cm")
            
            # Send to Pixhawk
            send_distance_message(distance)
            
            vl53.clear_interrupt()
        
        time.sleep(0.05) # 20Hz update rate
except KeyboardInterrupt:
    print("Stopping bridge...")