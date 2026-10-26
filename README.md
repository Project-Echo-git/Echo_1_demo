# Modular robot code

This project is built from separate modules that can be combined into robot capabilities. Each module has one job: read an input, interpret it, calculate a movement, or send a command.

`classes.py` stores the robot configuration and brings these modules together into skills. `launch.py` creates the robot and tells it which skill to perform. New capabilities are built by choosing the inputs, models, and controllers they need.

## Structure

| Layer | File | Responsibility |
| --- | --- | --- |
| Input | `percipio_rgb.py` | Supplies RGB frames from the Percipio camera. |
| Input, planned | `percipio_depth.py` | Future depth input. This module is not implemented yet. |
| Vision | `object_detection.py` | Detects COCO objects and returns a list of unique object names. |
| Vision | `face_tracker.py` | Detects faces and calculates its own X/Y pixel error. |
| Vision | `person_tracker.py` | Detects people and calculates its own X/Y pixel error. |
| Controller | `center_pixel_PID.py` | Converts X/Y pixel error into two neck servo angles. |
| Controller | `inverse_kinematics.py` | Placeholder for converting a 3D target into joint angles. |
| Output | `send_to_pico.py` | Opens a Pico connection and sends raw servo angles. |
| Robot and skills | `classes.py` | Stores robot information, Pico configuration, and combinations of modules that form skills. |
| Entry point | `launch.py` | Creates the robot and selects a skill to run. |

Face and person tracking each own their detection, target selection, smoothing, and error calculation. There is no separate `tracking.py`. The camera/display helpers used by the robot skills live in `classes.py`.

## How modules connect

For tracking:

```text
RGB frame → face or person tracker → X/Y pixel error → pixel PID → servo angles → Pico
```

For object recognition:

```text
RGB frame → object detector → object names → another skill or application
```

- Cameras provide frames through `read()` and close through `release()`.
- `FaceTracker.update(frame)` and `PersonTracker.update(frame)` return `(error_x, error_y)`. When no target is confirmed, they return `(None, None)` so the controller holds position.
- Positive X means right of the frame centre; positive Y means above it. Each tracker has its own configurable `target_point` inside the detected box. The existing face and person aim points are preserved.
- `TargetController.update(error_x, error_y)` returns `(angle_x, angle_y)` and sends them when a Pico is attached. Tracking is limited to 60–120 degrees.
- `ObjectDetector.detect(frame)` returns names such as `["bottle", "cup"]`. The existing exclusions for person, chair, and backpack remain configurable through `excluded_names`.
- `send_angles(part, *angles)` sends one angle per configured pin, in pin order.

## Robot skills

```python
from classes import Robot

robot = Robot(source="percipio", port="COM4")
robot.track_face()
```

Available skills are `track_face()`, `track_person()`, `object_detection()`, `non_verbal_yes()`, and `non_verbal_no()`. Camera skills run until Q or Escape is pressed or the preview window is closed. They release the camera and close their serial connection on exit.

Object detection can pass each frame's names to another function:

```python
robot.object_detection(on_objects=print)
```

It also returns the final frame's names when the preview closes. To use recognition without a preview loop, call the model directly:

```python
from object_detection import ObjectDetector
from percipio_rgb import PercipioCamera

model = ObjectDetector()
camera = PercipioCamera()
try:
    ok, frame = camera.read()
    if ok:
        names = model.detect(frame)
finally:
    camera.release()
```

The arm and hand definitions are retained as configuration work in progress. They are not connected to configured Picos. `wave_left()` and the IK solver raise `NotImplementedError` until their hardware and calculations are supplied.

## Launch

Run these commands with the project's Python environment:

```text
python launch.py
python launch.py --skill person
python launch.py --skill objects
python launch.py --skill face --source webcam --camera 0 --dry-run
python launch.py --skill face --port COM4
```

The default skill is face tracking with the Percipio camera. `--detector face` and `--detector person` remain accepted as aliases for `--skill`. `--dry-run` previews tracking without opening a Pico connection. `--debug-timing` prints the controller update rate.

## Pico setup

Picos are configured in the `PICOS` dictionary in `classes.py`. Currently, `neck` uses the Pico named `left_pico`, with GP28 first and GP19 second. Set its port explicitly when connecting multiple Picos; automatic detection requires exactly one connected Pico.

Copy `pico/pico_receiver.py` to the Pico as its single `code.py` file. It needs CircuitPython and the `adafruit_motor` library. The current receiver starts both servos at 90 degrees and accepts 0–180 degrees. Servos 3–5 are commented out for manual configuration.

```python
from classes import PICOS
from send_to_pico import send_angles

with PICOS["neck"]:
    send_angles("neck", 90, 90)
```

To add another Pico, add its part name, Pico name, port, and ordered pins in `classes.py`. Adjust that Pico's standalone receiver to use the same pins and servo count. The sender already supports different numbers of angles.

## Adding a capability

Add a method to `Robot` that combines the modules it needs. Use model output as input to a controller when movement is required, or use it directly for recognition tasks. Then call that method from `launch.py` or another robot skill. Keep model calculations in their own files and hardware communication in the sender.

## Checks

```text
python -m unittest discover -s tests
```

The tests use simulated cameras and serial connections. They do not verify physical camera capture or servo movement.
