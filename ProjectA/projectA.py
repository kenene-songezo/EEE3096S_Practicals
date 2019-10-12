from time import sleep
import time
import spidev
import RPi.GPIO as GPIO
spi = spidev.SpiDev()
spi.open(0,0)
spi.max_speed_hz = 200000

# Variables
buttons = (7,11,36,37)				# 7-changing reading interval, 11-Reset system time, 36-Dismiss alarm, 37-Start/Stop Monitoring
outputs = (0,1) # to be set
pressCount = 0
readingFrequency = 1				# At start of program the default reading frequeny is 1 second
start = False

def LDR():
	cbyte = 0b10000000
	r = spi.xfer2([1,cbyte,0])
	# 10-bit value from returned bytes (bits 14 to 23) counting from 0
	x = ((r[1]&7)<<8)+r[2]
	return x

def humidity_Sensor():
	cbyte = 0b10010000
	r = spi.xfer2([1,cbyte,0])
	# 10-bit value from returned bytes (bits 14 to 23) counting from 0
	x = ((r[1]&7)<<8)+r[2]
	voltage = round(((x*3.3)/1024),1)	# Humidity vloltage
	return voltage


def temperature_Sensor():
	cbyte = 0b10100000
	r = spi.xfer2([1,cbyte,0])
	# 10-bit value from returned bytes (bits 14 to 23) counting from 0
	x = ((r[1]&7)<<8)+r[2]
	voltage = (x*3.3)/1024				# temperature vloltage
	temp_Ambient = int((voltage-0.4)/0.0195)	# Ambient temperature
	return temp_Ambient

def DAC():
	vout = round((LDR()*humidity_Sensor())/1023,1)
	return vout

def RTC_time():
	rtc = time.localtime()
	current_time = time.strftime("%H:%M:%S", rtc)
	return current_time

print("Press red button to start logging")

def GPIOsetup():
	GPIO.setmode(GPIO.BOARD)
	GPIO.setwarnings(False)
	GPIO.setup(buttons, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	#GPIO.setup(outputs, GPIO.OUT)
def changeInterval(channel):
	global pressCount
	global readingFrequency
	if pressCount == 0:
		readingFrequency = 2
		pressCount = pressCount + 1
	elif pressCount == 1:
		readingFrequency = 5
		pressCount = pressCount + 1
	else :
		readingFrequency = 1
		pressCount = 0

def resetSystemTime(channel):
	count = 1

def dismissAlarm(channel):
	count = 2

def monitoring(channel):
	global start
	if start:
		start = False
	else :
		start = True

print("-----------------------------------------------------------------")
print("|{0:<10s}|{1:10s}|{2:9s}|{3:7s}|{4:6s}|{5:8s}|{6:7s}|".format("RTC Time", "Sys Timer", "Humidity", "Temp","Light","DAC out","Alarm"))
print("-----------------------------------------------------------------")

GPIOsetup()
GPIO.add_event_detect(7, GPIO.FALLING, callback=changeInterval, bouncetime=400)
GPIO.add_event_detect(11, GPIO.FALLING, callback=resetSystemTime, bouncetime=400)
GPIO.add_event_detect(36, GPIO.FALLING, callback=dismissAlarm, bouncetime=400)
GPIO.add_event_detect(37, GPIO.FALLING, callback=monitoring, bouncetime=400)

def main():
	if start:
		print("|{0:<10s}|{1:10s}|{2:9s}|{3:7s}|{4:6s}|{5:8s}|{6:7s}|".format(RTC_time()," ",str(humidity_Sensor())+" V",str(temperature_Sensor())+" C",str(LDR()),str(DAC())+" V"," "))
		sleep(readingFrequency)

if __name__ == "__main__":
	try:
		while True:
			main()
	except KeyboardInterrupt:
		print("Exiting gracefully")
		spi.close()

	finally:					# run on exit
		spi.close()				# clean up
		
		print "\n All cleaned up"

