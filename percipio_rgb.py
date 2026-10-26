import threading
import time



SERIAL_NUMBER = "207000160584"
INTERFACE_IP = "192.168.0.20"
CAMERA_IP = "192.168.0.21"
SUBNET_MASK = "255.255.255.0"


def _check(status, operation):
    if not status:
        raise RuntimeError(f"{operation}: {status.message()}")


class PercipioCamera:
    def __init__(self, serial_number=SERIAL_NUMBER, interface_ip=INTERFACE_IP):
        try:
            import vcamera
        except ImportError as exc:
            raise RuntimeError(
                "Percipio SDK is unavailable. Run with this project's .venv Python."
            ) from exc
        self._sdk = vcamera
        self._camera = None
        self._connected = False
        self._closed = False
        self._condition = threading.Condition()
        self._frame = None
        self._error = None
        _check(vcamera.CameraUtils.Init(True), "Initialize Percipio SDK")
        try:
            cameras = vcamera.CameraUtils.DiscoverCameras()
            info = next((item for item in cameras
                         if item.serial_number == serial_number
                         and item.interface_info.network_info.ip == interface_ip), None)
            if info is None:
                found = ", ".join(item.serial_number for item in cameras) or "none"
                raise RuntimeError(
                    f"Percipio {serial_number} not found on {interface_ip}. "
                    f"Detected serials: {found}. Check power/cable and close Percipio Viewer "
                    "and percipio_test.exe."
                )
            if info.network_info.ip != CAMERA_IP:
                raise RuntimeError(
                    f"Camera has IP {info.network_info.ip}; expected {CAMERA_IP}. "
                    "Run build/Release/percipio_test.exe once to configure its IP, then close it."
                )
            self._camera = vcamera.CameraFactory.GetCameraByCameraInfo(info)
            _check(self._camera.Connect(), "Connect camera (close other camera apps)")
            self._connected = True
            _check(self._camera.StopCapture(), "Stop previous capture")
            acquisition, status = self._camera.GetFeature("AcquisitionMode")
            _check(status, "Get AcquisitionMode")
            _check(acquisition.SetValue(2), "Enable continuous capture")
            _check(self._camera.SetSensorEnabled(vcamera.SensorType.Depth, False),
                   "Disable depth stream")
            _check(self._camera.SetSensorEnabled(vcamera.SensorType.Texture, True),
                   "Enable RGB stream")
            self._camera.RegisterFrameSetCallback(self._on_frames)
            _check(self._camera.StartCapture(), "Start RGB capture")
        except BaseException:
            self.release()
            raise

    def _on_frames(self, frames):
        try:
            image = frames.GetImage(self._sdk.SensorType.Texture)
            if not image.IsValid():
                return
            if image.pixel_format() != self._sdk.PixelFormat.Rgb24:
                raise RuntimeError(f"Expected RGB24 image, got {image.pixel_format()}")
            # This camera supplies OpenCV-compatible BGR bytes despite its RGB24 label.
            frame = image.to_numpy().copy()  # Own the buffer before the SDK recycles it.
            with self._condition:
                if not self._closed:
                    self._frame = frame  # Keep only the newest frame to avoid lag.
                    self._condition.notify_all()
        except Exception as exc:
            with self._condition:
                self._error = exc
                self._condition.notify_all()

    def read(self, timeout=10.0):
        deadline = time.monotonic() + timeout
        with self._condition:
            while self._frame is None and self._error is None and not self._closed:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RuntimeError("No Percipio RGB frame arrived. Check camera connection.")
                self._condition.wait(remaining)
            if self._error is not None:
                raise RuntimeError(f"Percipio frame conversion failed: {self._error}") from self._error
            if self._closed:
                return False, None
            frame, self._frame = self._frame, None
            return True, frame

    def release(self):
        with self._condition:
            if self._closed:
                return
            self._closed = True
            self._frame = None
            self._condition.notify_all()
        if self._connected:
            try:
                self._camera.StopCapture()
            finally:
                self._camera.Disconnect()
                self._connected = False


if __name__ == "__main__":
    camera = PercipioCamera()
    try:
        ok, frame = camera.read()
        if ok:
            print(f"Percipio RGB OK: {frame.shape[1]} x {frame.shape[0]}")
    finally:
        camera.release()

