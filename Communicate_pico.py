import argparse
import time

PORT = None
BAUD_RATE = 115200
START_ANGLE_X = 90.0
START_ANGLE_Y = 90.0
ANGLE_LIMITS_X = (60.0, 120.0)
ANGLE_LIMITS_Y = (60.0, 120.0)
# Increasing the angle must turn the camera toward a positive image error.
# Reverse the corresponding sign if an axis moves away from the face.
DIRECTION_X = 1
DIRECTION_Y = 1
DEAD_ZONE_PX = 3
MAX_SPEED = 80.0


# (Kp, Ki, Kd): start with proportional control; tune on the actual head.
# Output is degrees/second, input is face offset in pixels.
PID_X = (0.2, 0.0, 0)
PID_Y = (0.2, 0.0, 0)


def clamp(value, low, high):
    return max(low, min(high, value))


class PID:
    def __init__(self, kp, ki, kd):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.reset()

    def reset(self):
        self.integral = 0.0
        self.previous_error = None

    def update(self, error, dt):
        if abs(error) <= DEAD_ZONE_PX:
            self.reset()
            return 0.0

        derivative = 0.0
        if self.previous_error is not None:
            derivative = (error - self.previous_error) / dt
        integral = clamp(self.integral + error * dt, -500.0, 500.0)
        raw_speed = self.kp * error + self.ki * integral + self.kd * derivative
        speed = clamp(raw_speed, -MAX_SPEED, MAX_SPEED)
        if speed == raw_speed or error * raw_speed < 0:
            self.integral = integral
        self.previous_error = error
        return speed


class FaceController:
    def __init__(self, pico=None):
        self.pico = pico
        self.pid_x = PID(*PID_X)
        self.pid_y = PID(*PID_Y)
        self.angle_x = START_ANGLE_X
        self.angle_y = START_ANGLE_Y
        self.previous_time = None

    def update(self, error_x, error_y, frame_width, frame_height):
        if error_x is None or error_y is None:
            self.pid_x.reset()
            self.pid_y.reset()
            self.previous_time = None
            return

        now = time.monotonic()
        dt = 1.0 / 30.0 if self.previous_time is None else now - self.previous_time
        if dt > 0.25:
            self.pid_x.reset()
            self.pid_y.reset()
        dt = clamp(dt, 0.001, 0.1)
        self.previous_time = now

        # Head-mounted camera: image error requests angular velocity (deg/s).
        # Integrate from the current angle; centred faces hold that angle.
        speed_x = DIRECTION_X * self.pid_x.update(error_x, dt)
        speed_y = DIRECTION_Y * self.pid_y.update(error_y, dt)
        next_x = self.angle_x + speed_x * dt
        next_y = self.angle_y + speed_y * dt
        self.angle_x = clamp(next_x, *ANGLE_LIMITS_X)
        self.angle_y = clamp(next_y, *ANGLE_LIMITS_Y)
        # Avoid integral windup when either servo reaches its travel limit.
        if self.angle_x != next_x:
            self.pid_x.integral = 0.0
        if self.angle_y != next_y:
            self.pid_y.integral = 0.0

        command = f"{self.angle_x:.2f},{self.angle_y:.2f}\n"
        if self.pico is not None:
            self.pico.write(command.encode("ascii"))
        else:
            print(f"error=({error_x}, {error_y}) px -> angles={command.strip()}")


def find_pico_port():
    from serial.tools import list_ports

    candidates = [p.device for p in list_ports.comports() if p.vid in (0x2E8A, 0x239A)]
    if len(candidates) != 1:
        raise RuntimeError("Set PORT or pass --port with your Pico's USB serial port.")
    return candidates[0]


def main():
    from face_recognition import main as track_face

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default=PORT)
    parser.add_argument("--source", choices=("percipio", "webcam"), default="percipio",
                        help="Camera source (default: Percipio RGB)")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index with --source webcam")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        track_face(on_face=FaceController().update, camera_index=args.camera, source=args.source)
        return

    import serial

    port = args.port or find_pico_port()
    with serial.Serial(port, BAUD_RATE, timeout=1, write_timeout=1) as pico:
        print(f"Sending servo angles to {port}. Press Q in the camera window to stop.")
        controller = FaceController(pico)
        pico.write(f"{controller.angle_x:.2f},{controller.angle_y:.2f}\n".encode("ascii"))
        track_face(on_face=controller.update, camera_index=args.camera, source=args.source)


if __name__ == "__main__":
    main()

