import time

import board
import pwmio
from adafruit_motor import servo

#rechts = coms 4

pwm_1 = pwmio.PWMOut(board.GP28, frequency=50)
pwm_2 = pwmio.PWMOut(board.GP19, frequency=50)
#pwm_3 = pwmio.PWMOut(board.GP18, frequency=50)
#pwm_4 = pwmio.PWMOut(board.GP17, frequency=50)
#pwm_5 = pwmio.PWMOut(board.GP16, frequency=50)

servo_1 = servo.Servo(pwm_1, min_pulse=500, max_pulse=2500, actuation_range=270)
servo_2 = servo.Servo(pwm_2, min_pulse=500, max_pulse=2500, actuation_range=270)

#servo_3 = servo.Servo(pwm_3, min_pulse=500, max_pulse=2500, actuation_range=270)
#servo_4 = servo.Servo(pwm_4, min_pulse=500, max_pulse=2500, actuation_range=270)
#servo_5 = servo.Servo(pwm_5, min_pulse=500, max_pulse=2500)

while True:
    
    servo_1.angle = 90
    servo_2.angle = 60
    time.sleep(0.7)
    servo_2.angle = 120
    servo_1.angle = 30
    time.sleep(0.7)

    
    










