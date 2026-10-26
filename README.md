# Face tracker

Run `launch.py` to track faces using the Percipio camera and left Pico. Use `--detector person`, `--source webcam`, `--port COM4`, or `--dry-run` as needed.

## Sending angles

`send_to_pico.py` contains the `Pico` class and `PICOS` registry. Each Pico has a name, port, and ordered pins. The left Pico is registered as `left_arm`, with GP28 followed by GP19. Its port is automatically detected when exactly one Pico is connected; set `port="COM4"` in the registry or use `--port` to select it explicitly.

```python
from send_to_pico import PICOS, send_angles

with PICOS["left_arm"]:
    send_angles("left_arm", 90, 90)
```

Angles are sent unchanged as comma-separated degrees, rounded to two decimals, followed by a newline. Supply one angle per pin, in the same order. Calls reuse the connection; use a `with` block or call the Pico's `close()` when finished.

## Pico files

Copy `pico/pico_receiver.py` onto the CircuitPython drive. Copy `pico/pico_receiver_left.py` onto that drive as `code.py`. Install `adafruit_motor` in the drive's `lib` directory.

The left receiver uses GP28 and GP19, starts at 90 degrees, and accepts angles from 60 to 120 degrees. PWM remains 50 Hz with 500–2500 microsecond pulses and a 270-degree actuation range.

To add another Pico, add a registry entry with its part name, Pico name, pins, and explicit COM port. Create its own receiver file using the same pattern as `pico_receiver_left.py`, with matching pins in matching order. `run(pins, angle_limits=(60, 120))` accepts any number of pins; choose limits appropriate for that hardware. Copy the shared receiver and the new receiver as `code.py` onto that Pico. The sender needs no other changes for 2, 4, or 5 servos.

## Tracking files

- `launch.py`: detector, camera, and connection setup.
- `person_tracker.py`: shared camera loop for both detectors.
- `face_detector.py` / `person_detection.py`: detectors.
- `face_tracker.py`: target selection and smoothing.
- `controller.py`: two-axis PID control, with 60–120 degree limits.
- `percipio_camera.py`: Percipio connection and IP settings.
- `classes.py`: unfinished robot gestures, separate from the tracking launcher.

The tracking controller still drives two servos. New robot parts can use `send_angles(part, *angles)` directly.
