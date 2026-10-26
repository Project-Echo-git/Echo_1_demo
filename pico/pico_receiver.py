import sys
import time
import supervisor
import pwmio
from adafruit_motor import servo


def run(pins, angle_limits=(60, 120)):
    servos = [
        servo.Servo(pwmio.PWMOut(pin, frequency=50),
                    min_pulse=500, max_pulse=2500, actuation_range=270)
        for pin in pins
    ]
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
