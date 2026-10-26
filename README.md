# Face tracker

Tracks a face or person and moves two servos through a Raspberry Pi Pico.
Works with the Percipio camera or a webcam.

## Files

- `launch.py` - starts face tracking using the project Python environment.
- `face_recognition.py` - detects faces.
- `person.py` - detects people using YOLO.
- `face_target.py` - picks a target and smooths its position.
- `Communicate_pico.py` - PID control and sends servo angles to the Pico.
- `percipio_camera.py` - connects to the Percipio camera. Camera IP and serial number are set here.
- `pico/pico_receiver.py` - receives angles on the Pico ( this is the main pico file in code.py)
- `pico/pico_raw_angles.py` - basic servo movement test.
- `models/yolo26n.pt` - YOLO model.


`.venv/` holds Python packages. `build/` and `deps/` are left over from the C++ camera test. CMake is not needed for Python tracking.

## Run

From the project folder, with the Python environment and dependencies installed:

```powershell
# Face tracking
.\.venv\Scripts\python.exe launch.py --port COM4

# Person tracking
.\.venv\Scripts\python.exe person.py --port COM4

# Webcam preview, no servo movement
.\.venv\Scripts\python.exe launch.py --source webcam --dry-run
```

Change `COM4` to your Pico's port. Press Q to stop.
The default camera is Percipio. Servo limits are 60-120 degrees on both the PC and Pico.
