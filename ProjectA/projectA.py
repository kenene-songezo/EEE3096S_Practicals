from time import sleep
import blynklib
import threading
import subprocess
import time
import spidev
import RPi.GPIO as GPIO
spi = spidev.SpiDev()
spi.open(0,0)
spi.max_speed_hz = 200000

# Variables
buttons = (7,11,29,31)				# 7-changing reading interval, 11-Reset system time, 36-Dismiss alarm, 37-Start/Stop Monitoring
outputs = 32 # to be set
pressCount = 0
readingFrequency = 1				# At start of program the default reading frequeny is 1 second
start = False
start_time = time.time()
alarm = " "
already_set = False
temperature = float(0)
light       = int(0)
humidity    = float(0)
alarm_Dismissed = False
count = 0


BLYNK_AUTH = 'XAP_7Kc-Yc7G3ihdnLJ_hpHT50vJWXRt'
blynk = blynklib.Blynk(BLYNK_AUTH)


def LDR():
	#Function to read Light values from the ADC

	cbyte = 0b10000000
	r = spi.xfer2([1,cbyte,0])
	# 10-bit value from returned bytes (bits 14 to 23) counting from 0
	light = ((r[1]&7)<<8)+r[2]
	return light

def humidity_Sensor():
	#Function to read potentiometer values from ADC

	cbyte = 0b10010000
	r = spi.xfer2([1,cbyte,0])
	# 10-bit value from returned bytes (bits 14 to 23) counting from 0
	x = ((r[1]&7)<<8)+r[2]
	humidity = round(((x*3.3)/1024),1)	# Humidity vloltage
	return humidity

def temperature_Sensor():
	#Function to read temperature values via the ADC

	cbyte = 0b10100000
	r = spi.xfer2([1,cbyte,0])
	# 10-bit value from returned bytes (bits 14 to 23) counting from 0
	x = ((r[1]&7)<<8)+r[2]
	voltage = (x*3.3)/1024				# temperature vloltage
	temp = int((voltage-0.4)/0.0195)	# Ambient temperature
	return temp

def DAC():
	# Function to calculate and return voltage to be sent via the ADC

	vout = round((light*humidity)/1023,1)
	return vout

def RTC_time():
	# Function to get the time using kernel driver

	rtc = time.localtime()
	current_time = time.strftime("%H:%M:%S", rtc)
	return current_time

def elapsed_time(now, beginning):
	# Function used by other functions to calculate time elapsed (including System time)
	elapsed_time = now-beginning
	return elapsed_time

def systemTime():
	# Function to get the system time and return a string formatted time

	global start_time
	time_now = time.time()
	time_elapsed = elapsed_time(time_now,start_time)
	systemTime = time.strftime("%H:%M:%S",time.gmtime(time_elapsed))
	return systemTime


def changeInterval(channel):
	# callback function when reading interval button is pressed channel 7

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
	# callback function when reset system time button is pressed channel 11
	global start_time
	global pressCount
	global readingFrequency
	global start_time
	global alarm
	global already_set
	global alarm_Dismissed
	global count 
	start_time = time.time()
	blynk.virtual_write(6,'clr')
	pressCount = 0
	readingFrequency = 1				# At start of program the default reading frequeny is 1 second
	start_time = time.time()
	alarm = " "
	already_set = True
	alarm_Dismissed = True
	count = 0

def dismissAlarm(channel):
	# callback function to dismiss alarm when it goes off 29
	global alarm_Dismissed
	alarm_Dismissed = True
	

def monitoring(channel):
	# call back function to start/stop monitoring when red button pressed channel 31

	global start
	if start:
		start = False
		blynk.virtual_write(6,"not logging, press red button to start logging")
	else :
		start = True
		blynk.virtual_write(6,"Started logging")

def GPIOsetup():
	GPIO.setmode(GPIO.BOARD)
	GPIO.setwarnings(False)
	GPIO.setup(buttons, GPIO.IN, pull_up_down=GPIO.PUD_UP)
	GPIO.add_event_detect(7, GPIO.FALLING, callback=changeInterval, bouncetime=400)
	GPIO.add_event_detect(11, GPIO.FALLING, callback=resetSystemTime, bouncetime=400)
	GPIO.add_event_detect(29, GPIO.FALLING, callback=dismissAlarm, bouncetime=400)
	GPIO.add_event_detect(31, GPIO.FALLING, callback=monitoring, bouncetime=400)
	GPIO.setup(outputs, GPIO.OUT)


print("Press red button to start logging")

print("-----------------------------------------------------------------")
print("|{0:<10s}|{1:10s}|{2:9s}|{3:7s}|{4:6s}|{5:8s}|{6:7s}|".format("RTC Time", "Sys Timer", "Humidity", "Temp","Light","DAC out","Alarm"))
print("-----------------------------------------------------------------")

GPIOsetup()
LED_alarm = GPIO.PWM(outputs, 50)
dc = 0
def main():
	if start:
		global alarm
		global start_alarm
		global already_set
		global light
		global humidity
		global temperature
		global count
		global LED_alarm
		global dc
		RTCtime     = RTC_time()
		systime     = systemTime()

		light       = LDR()
		humidity    = humidity_Sensor()
		temperature = temperature_Sensor()
		time.sleep(readingFrequency)
		# Threading
		# threads_list= []
		# thread  = threading.Thread(target = readADC, name = 'thread1')
		# thread.start()
		# thread.join()
		blynk.virtual_write(9,light)
		blynk.virtual_write(7, temperature)
		blynk.virtual_write(8,humidity)
		blynk.virtual_write(10,RTCtime)
		blynk.virtual_write(11,systime)
		vout = DAC()
		output ="|{0:<10s}|{1:10s}|{2:9s}|{3:7s}|{4:6s}|{5:8s}|{6:7s}|".format(RTCtime,systemTime(),str(humidity)+" V",str(temperature)+" C",str(light),str(vout)+" V",alarm) 
		print(output)

		if vout<0.65 or vout>2.65:
			if (already_set == False):
				start_alarm = time.time()
				alarm = "*"
				LED_alarm.start(dc)
				blynk.virtual_write(6,'Alarm at {}'.format(RTCtime))
				blynk.notify("Alarm ringing, Switch it off at the green house")
				already_set = True
			if dc ==100:
				dc = 0
			LED_alarm.ChangeDutyCycle(dc)
			dc = dc+20
			if (already_set == True) :
				if (alarm_Dismissed==True):
					time_sinceAlarm = elapsed_time(time.time(),start_alarm)
					seconds = ((time_sinceAlarm%31557600)%86400)%3600
					minutes = seconds/60
					alarm = " "
					LED_alarm.stop()
					if count == 0:
						blynk.virtual_write(6,'Alarm dismissed at {}'.format(RTCtime))
						count = 1
					if minutes > 3:
						already_set = False
						count = 0
		else:
			if(alarm_Dismissed==True):
				alarm = " "
				if count == 0:
					blynk.virtual_write(6,'Alarm dismissed at {}'.format(RTCtime))
					count = 1
					LED_alarm.stop()
			else:
				if dc == 100:
					dc = 0
				LED_alarm.ChangeDutyCycle(dc)
				dc = dc + 20


if __name__ == "__main__":
	try:
		while True:
			main()
			blynk.run()
	except KeyboardInterrupt:
		print("Exiting gracefully")
		spi.close()
		GPIO.cleanup()

	finally:					# run on exit
		spi.close()				# clean up
		GPIO.cleanup()
		print "\n All cleaned up"

