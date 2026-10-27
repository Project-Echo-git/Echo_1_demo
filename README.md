# Modular robot code

The robot's capabilities are built from separate modules. Start by choosing a skill, or combine the modules into a new one. `classes.py` defines the robot and its skills; `launch.py` provides a terminal chat that turns prompts into skills using Llama 3.2 1B through local Ollama. No OpenAI API key or credits are needed.

## What the robot can do

| Skill | Call | What it does |
| --- | --- | --- |
| Follow a face | `robot.track_face()` | Uses face position to steer the neck. |
| Follow a person | `robot.track_person()` | Uses person position to steer the neck. |
| Recognise objects | `robot.detect_objects()` | Reports a consistent object, waiting up to 20 seconds when nothing is confirmed. |
| Nod yes | `robot.nod_yes()` | Moves the neck's pitch servo through a nod. |
| Shake no | `robot.shake_no()` | Moves the neck's yaw servo from side to side. |


```python
from classes import Robot

robot = Robot(source="percipio", port="COM4")
robot.track_face()
```

Face and person tracking run until Q or Escape is pressed or the preview window is closed. Object recognition finishes when an object is confirmed, or after a 20-second timeout. Camera skills release the camera and close their serial connection on exit.

Object recognition keeps checking the latest 40 frames and requires at least 25 sightings of an object. Each object gets one vote per frame. The most frequent qualifying name is printed once as `the detected object is: cup` and returned. If nothing is confirmed, it keeps looking and only prints `the detected object is: none` after 20 seconds. The timeout starts after the first detection finishes, excluding model startup. Q, Escape, or closing the preview cancels without printing `none`. Set `DETECTION_FRAMES`, `MIN_DETECTIONS`, and `DETECTION_TIMEOUT` in `object_detection.py` to adjust this.

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

## Run the robot chat

Run this from the project folder:

```powershell
python launch.py
```

Type a prompt at `You >`. The robot replies, displays the selected skills, and runs them in order. Conversation stays in memory until you exit or use `/clear`.

| Prompt | Behaviour |
| --- | --- |
| `look at me` | Starts person tracking. |
| `look at my face` | Starts face tracking. |
| `nod twice then shake your head` | Runs two nods followed by one head shake. |
| `is 2 + 2 = 4?` | Answers yes and nods. |
| `is 7 * 8 = 54?` | Answers no and shakes its head. |
| `is the sun a star?` | Uses the model's yes/no answer to choose the gesture. |
| `what is 2 plus 2?` | Gives a text answer without a yes/no gesture. |
| `what is this object?` | Starts object detection and reports the detected name. |

Simple numeric comparisons are calculated directly. Other questions use Llama, so answers can be wrong. Keep prompts short and clear. The interface displays text; it does not provide speech input or audio replies.

| Chat command | What it does |
| --- | --- |
| `/skills` | Lists the available skill names. |
| `/clear` | Clears the conversation history. |
| `/exit` | Closes the chat. `exit` and `quit` also work. |

Skills run sequentially. While tracking is active, press Q or Escape in the camera window, or close that window, to return to the chat or continue the next skill. The chat does not accept another prompt while a skill is running. Timed tracking, simultaneous skills, and decisions based on future sensor results are not supported.

### Run one prompt or skill

A quoted prompt runs once and then exits:

```powershell
python launch.py "nod twice then shake your head"
```

Exact skill names bypass Llama and do not require Ollama:

```powershell
python launch.py track_face
python launch.py track_person
python launch.py detect_objects
python launch.py nod_yes
python launch.py shake_no
```

`python launch.py --help` shows the launcher arguments. Use `/skills` in the chat to list skills. Set camera and Pico configuration in `classes.py`; the launcher uses `Robot()` with those defaults.

## Local model setup

The Windows launcher expects the project's Python environment at `.venv/Scripts/python.exe`, with the robot's camera, vision, and serial dependencies installed. It switches to that environment automatically. Ollama is a separate program; the launcher calls its local HTTP API using Python's standard library.

For a fresh clone:

1. Install [Ollama for Windows](https://ollama.com/download/windows) and start it.
2. Download the model once:

   ```powershell
   ollama pull llama3.2:1b
   ```

3. Run `python launch.py` from the project folder.

The model download is about 1.3 GB. Once downloaded, chat runs locally without API credits. Ollama must listen on `127.0.0.1:11434` and have `llama3.2:1b` available.

This project also supports a portable setup. If no server is running, the launcher starts `deps/ollama/ollama.exe`, uses `models/ollama/` for model weights, and keeps Ollama's local configuration under `deps/ollama/.ollama/`. The portable model must already be downloaded; the launcher does not download it automatically. If an Ollama server is already running, its own model storage is used instead.

The first reply can take longer while the model loads. Ollama keeps the model loaded for five minutes after a request. Exiting the chat does not shut down the Ollama server.

### Files kept out of Git

These folders are local dependencies and are ignored:

```text
deps/ollama/
models/ollama/
```

Do not commit the Ollama executable, libraries, model weights, or its private key (`deps/ollama/.ollama/id_ed25519`). Anyone cloning the repository installs Ollama and downloads Llama separately. The object detector uses the separate `models/yolo26s.pt` file, which remains tracked in Git.

## Build a new skill

A skill is a method on `Robot` in `classes.py`. It combines existing modules into a capability that `launch.py` or another skill can call.

1. Decide what the robot should do and what output the skill should provide.
2. Choose its inputs and models. Add a controller and Pico connection when it needs movement.
3. Add a method to `Robot` that connects those modules. Keep detection and tracking calculations in the model files; keep angle calculations in the controller.
4. Call the method directly, or add its method name to `SKILLS` in `launch.py`. Update the model instructions and examples in `get_response()` so prompts can select it. The direct command uses the same method name.

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
| Entry point | `launch.py` | Runs local Llama chat, checks simple math comparisons, and executes selected robot skills. |

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

