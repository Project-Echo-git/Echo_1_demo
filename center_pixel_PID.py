import time

START_ANGLE_X = 90.0
START_ANGLE_Y = 90.0
ANGLE_LIMITS_X = (60.0, 120.0)
ANGLE_LIMITS_Y = (60.0, 120.0)


DIRECTION_X = -1
DIRECTION_Y = 1
DEAD_ZONE_PX = 3
MAX_SPEED = 90.0

D_ALPHA = 0.25
PID_X = (0.27, 0.0, 0.145)
PID_Y = (0.27, 0.0, 0.145)


def clamp(value, low, high):
    return max(low, min(high, value))


class PID:
    def __init__(self, kp, ki, kd):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.reset()

    def reset(self):
        self.integral = 0.0
        self.previous_error = None
        self.d_filtered = 0.0

    def update(self, error, dt):
        if abs(error) <= DEAD_ZONE_PX:
            self.reset()
            return 0.0

        raw_derivative = 0.0
        if self.previous_error is not None:
            raw_derivative = (error - self.previous_error) / dt
        self.d_filtered += D_ALPHA * (raw_derivative - self.d_filtered)
        integral = clamp(self.integral + error * dt, -500.0, 500.0)
        raw_speed = self.kp * error + self.ki * integral + self.kd * self.d_filtered
        speed = clamp(raw_speed, -MAX_SPEED, MAX_SPEED)
        if speed == raw_speed or error * raw_speed < 0:
            self.integral = integral
        self.previous_error = error
        return speed


class TargetController:
    def __init__(self, pico=None, debug_timing=False):
        self.pico = pico
        self.pid_x = PID(*PID_X)
        self.pid_y = PID(*PID_Y)
        self.angle_x = START_ANGLE_X
        self.angle_y = START_ANGLE_Y
        self.previous_time = None
        self.debug_timing = debug_timing
        self._timing_previous = None
        self._timing_started = None
        self._timing_intervals = []

    def _report_timing(self):
        now = time.perf_counter()
        if self._timing_previous is None:
            self._timing_previous = self._timing_started = now
            return
        self._timing_intervals.append(now - self._timing_previous)
        self._timing_previous = now
        if now - self._timing_started >= 1.0:
            intervals = self._timing_intervals
            average = sum(intervals) / len(intervals)
            rate = 1.0 / average if average > 0 else 0.0
            print(f"[timing] update interval: avg={average * 1000:.1f} ms "
                  f"min={min(intervals) * 1000:.1f} ms "
                  f"max={max(intervals) * 1000:.1f} ms | {rate:.1f} Hz")
            self._timing_intervals = []
            self._timing_started = now

    def update(self, error_x, error_y):
        if self.debug_timing:
            self._report_timing()
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

        speed_x = DIRECTION_X * self.pid_x.update(error_x, dt)
        speed_y = DIRECTION_Y * self.pid_y.update(error_y, dt)
        next_x = self.angle_x + speed_x * dt
        next_y = self.angle_y + speed_y * dt
        self.angle_x = clamp(next_x, *ANGLE_LIMITS_X)
        self.angle_y = clamp(next_y, *ANGLE_LIMITS_Y)
        if self.angle_x != next_x:
            self.pid_x.integral = 0.0
        if self.angle_y != next_y:
            self.pid_y.integral = 0.0

        command = f"{self.angle_x:.2f},{self.angle_y:.2f}\n"
        if self.pico is not None:
            self.pico.send_angles(self.angle_x, self.angle_y)
        else:
            print(f"error=({error_x}, {error_y}) px -> angles={command.strip()}")
        return self.angle_x, self.angle_y
