# Modular robot code

The robot's capabilities are built from separate modules. Start by choosing a skill, or combine the modules into a new one. `classes.py` defines the robot and its skills; `launch.py` tells it which skill to perform.

## What the robot can do

| Skill | Call | What it does |
| --- | --- | --- |
| Follow a face | `robot.track_face()` | Uses face position to steer the neck. |
| Follow a person | `robot.track_person()` | Uses person position to steer the neck. |
| Recognise objects | `robot.detect_objects()` | Reports a consistent object, waiting up to 30 seconds when nothing is confirmed. |
| Nod yes | `robot.nod_yes()` | Moves the neck's pitch servo through a nod. |
| Shake no | `robot.shake_no()` | Moves the neck's yaw servo from side to side. |


```python
from classes import Robot

robot = Robot(source="percipio", port="COM4")
robot.track_face()
```

Face and person tracking run until Q or Escape is pressed or the preview window is closed. Object recognition finishes when an object is confirmed, or after a 30-second timeout. Camera skills release the camera and close their serial connection on exit.

Object recognition keeps checking the latest 50 frames and requires at least 25 sightings of an object. Each object gets one vote per frame. The most frequent qualifying name is printed once as `the detected object is: cup` and returned. If nothing is confirmed, it keeps looking and only prints `the detected object is: none` after 30 seconds. The timeout starts after the first detection finishes, excluding model startup. Q, Escape, or closing the preview cancels without printing `none`. Set `DETECTION_FRAMES`, `MIN_DETECTIONS`, and `DETECTION_TIMEOUT` in `object_detection.py` to adjust this.

The selected name can also be passed to another function:

```python
robot.detect_objects(on_objects=print)
```

The callback receives one confirmed name when recognition finishes. To get raw per-frame detections, call the model directly:

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

### Run a skill

Run one command from the project folder. The skill name is the only input, and it matches the method on `Robot`:

```text
python launch.py track_face
python launch.py track_person
python launch.py detect_objects
python launch.py nod_yes
python launch.py shake_no
```

`python launch.py --help` lists the available skills. Set camera and Pico configuration in `classes.py`; the launcher uses `Robot()` with those defaults. It automatically uses the project's Python environment.

## Build a new skill

A skill is a method on `Robot` in `classes.py`. It combines existing modules into a capability that `launch.py` or another skill can call.

1. Decide what the robot should do and what output the skill should provide.
2. Choose its inputs and models. Add a controller and Pico connection when it needs movement.
3. Add a method to `Robot` that connects those modules. Keep detection and tracking calculations in the model files; keep angle calculations in the controller.
4. Call the method directly, or add its method name to `SKILLS` in `launch.py`. The command will use that same name.

For example, a new skill can recognise objects from one RGB frame and return their names. Add this method inside `Robot`:

```python
def read_objects(self):
    from object_detection import ObjectDetector, open_camera

    detector = ObjectDetector()
    camera = open_camera(self.source, self.camera_index)
    try:
        ok, frame = camera.read()
        if not ok:
            raise RuntimeError("Cannot read camera.")
        return detector.detect(frame)
    finally:
        camera.release()
```

Then call it with `names = robot.read_objects()`. A later skill can use those names to decide what to do next.

For a movement skill, follow the same pattern as face tracking: connect the tracker's `(error_x, error_y)` output to the pixel PID, then send the resulting angles to the selected Pico. Other controllers can use different inputs while producing the same raw-angle output.

## Structure

| Layer | File | Responsibility |
| --- | --- | --- |
| Input | `percipio_rgb.py` | Supplies RGB frames from the Percipio camera. |
| Input, planned | `percipio_depth.py` | Future depth input. This module is not implemented yet. |
| Vision | `object_detection.py` | Detects COCO objects and returns a list of unique object names. |
| Vision | `face_tracker.py` | Detects faces and calculates its own X/Y pixel error. |
| Vision | `person_tracker.py` | Detects people and calculates its own X/Y pixel error. |
| Controller | `center_pixel_PID.py` | Converts X/Y pixel error into two neck servo angles. |
| Motion | `neck_gestures.py` | Runs the neck nod and shake sequences used by robot skills. |
| Controller | `inverse_kinematics.py` | Placeholder for converting a 3D target into joint angles. |
| Output | `send_to_pico.py` | Opens a Pico connection and sends raw servo angles. |
| Robot and skills | `classes.py` | Stores robot information, Pico configuration, and combinations of modules that form skills. |
| Entry point | `launch.py` | Creates the robot and selects a skill to run. |

Face and person tracking each own their detection, target selection, smoothing, and error calculation. There is no separate `tracking.py`. Each tracker contains its complete camera, detection, calculation, and display loop. `classes.py` connects these modules to controllers and Picos as robot skills.

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

## Checks

```text
python -m unittest discover -s tests
```

The tests use simulated cameras and serial connections. They do not verify physical camera capture or servo movement.

