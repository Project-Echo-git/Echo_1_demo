import sys
import time
import supervisor
import pwmio
import board
from adafruit_motor import servo

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

servos=[servo_1, servo_2]
angle_limits = (0, 180)

for motor in servos:
    motor.angle = 90
line = ""
while True:
    if supervisor.runtime.serial_bytes_available:
        char = sys.stdin.read(1)
        if char == "\n":
            try:
                angles = [float(value) for value in line.strip().split(",")]
                if (len(angles) == len(servos)
                        and all(angle_limits[0] <= angle <= angle_limits[1]
                                for angle in angles)):
                    for motor, angle in zip(servos, angles):
                        motor.angle = angle
            except ValueError:
                pass
            line = ""
        else:
            line += char
    else:
        time.sleep(0.005)
