import sys
import time
import supervisor
import board
import pwmio
from adafruit_motor import servo

pan = servo.Servo(pwmio.PWMOut(board.GP28, frequency=50),
                  min_pulse=500, max_pulse=2500, actuation_range=270)
tilt = servo.Servo(pwmio.PWMOut(board.GP19, frequency=50),
                   min_pulse=500, max_pulse=2500, actuation_range=270)
pan.angle = tilt.angle = 90
line = ""
while True:
    if supervisor.runtime.serial_bytes_available:
        char = sys.stdin.read(1)
        if char == "\n":
            try:
                x, y = map(float, line.strip().split(","))
                if 60 <= x <= 120 and 60 <= y <= 120:
                    pan.angle, tilt.angle = x, y
            except ValueError:
                pass
            line = ""
        elif len(line) < 64:
            line += char
        else:
            line = ""
    else:
        time.sleep(0.005)
