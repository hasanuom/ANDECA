import time
import board
import adafruit_vl53l4cd

i2c = board.I2C()
vl53 = adafruit_vl53l4cd.VL53L4CD(i2c)

vl53.inter_measurement = 0
vl53.timing_budget = 50

print("Distance sensor active")
print("CTRL+C to stop")

vl53.start_ranging()

while True:
	if vl53.data_ready:
		distance = vl53.distance
		print(f"Distance: {distance:.2f} cm")
		vl53.clear_interrupt()
		
	time.sleep(0.01)
