import math
import time
import cv2


class FaceTracker:
    name = "face"
    target_point = (0.47, 0.3)

    def __init__(self):
        self.target = StableTarget(*self.target_point)
        self.model = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        if self.model.empty():
            raise RuntimeError("Could not load the OpenCV face detector.")

    def detect(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return self.model.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=8, minSize=(50, 50)
        )

    def update(self, frame):
        self.boxes = self.detect(frame)
        self.point = self.target.update(self.boxes)
        self.box = self.target.box
        if self.point is None:
            return None, None
        height, width = frame.shape[:2]
        x, y = map(round, self.point)
        return x - width // 2, height // 2 - y


    def run(self, source="percipio", camera_index=0, on_target=None):
        return run_tracking(self, source, camera_index, on_target)


class StableTarget:
    def __init__(self, point_x=0.47, point_y=0.3):
        self.point_x = point_x
        self.point_y = point_y
        self.reset()

    def reset(self):
        self.box = None
        self.count = 0
        self.confirmed = False
        self.point = None
        self.last_seen = None
        self.started = None

    def update(self, boxes, now=None):
        now = time.monotonic() if now is None else now
        boxes = [tuple(map(float, box)) for box in boxes]
        if self.last_seen is not None and now - self.last_seen > 0.5:
            self.reset()
        selected = None
        if self.box is not None:
            x, y, w, h = self.box
            matches = []
            for candidate in boxes:
                cx, cy, cw, ch = candidate
                distance = math.hypot(cx + cw / 2 - x - w / 2, cy + ch / 2 - y - h / 2)
                if (0.65 <= cw / w <= 1.55 and 0.65 <= ch / h <= 1.55
                        and distance <= 0.6 * max(w, h)):
                    matches.append((distance, candidate))
            if matches:
                selected = min(matches, key=lambda item: item[0])[1]
        elif boxes:
            selected = max(boxes, key=lambda box: box[2] * box[3])
        if selected is None:
            if not self.confirmed:
                self.reset()
            self.point = None
            return None
        dt = 0 if self.last_seen is None else now - self.last_seen
        if self.started is None:
            self.started = now
        self.box = selected
        self.last_seen = now
        self.count += 1
        self.confirmed = self.confirmed or (self.count >= 4 and now - self.started >= 0.15)
        if not self.confirmed:
            return None
        x, y, w, h = selected
        point = (x + w * self.point_x, y + h * self.point_y)
        if self.point is not None:
            alpha = 1 - math.exp(-max(dt, 0) / 0.08)
            point = tuple(old + alpha * (new - old) for old, new in zip(self.point, point))
        self.point = point
        return point


def open_camera(source, camera_index=0):
    if source == "percipio":
        from percipio_rgb import PercipioCamera

        return PercipioCamera()
    if source == "webcam":
        camera = cv2.VideoCapture(camera_index)
        if not camera.isOpened():
            camera.release()
            raise RuntimeError(f"Cannot open webcam {camera_index}.")
        return camera
    raise ValueError(f"Unknown camera source: {source}")


def run_tracking(detector, source="percipio", camera_index=0, on_target=None):
    window = f"{detector.name.capitalize()} tracking - Q to quit"
    camera = open_camera(source, camera_index)
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError(
                    f"Cannot read {source} camera. Close other camera apps and check the connection."
                )
            error = detector.update(frame)
            boxes = detector.boxes
            point = detector.point
            height, width = frame.shape[:2]
            cx, cy = width // 2, height // 2
            cv2.drawMarker(frame, (cx, cy), (255, 255, 0), cv2.MARKER_CROSS, 16, 2)
            for x, y, w, h in boxes:
                cv2.rectangle(frame, (round(x), round(y)),
                              (round(x + w), round(y + h)), (100, 100, 100), 1)
                dot = (round(x + w * detector.target_point[0]),
                       round(y + h * detector.target_point[1]))
                cv2.circle(frame, dot, 4, (0, 255, 255), -1)

            if point is not None:
                px, py = map(round, point)
                x, y, w, h = detector.box
                cv2.rectangle(frame, (round(x), round(y)),
                              (round(x + w), round(y + h)), (0, 255, 0), 2)
                cv2.circle(frame, (px, py), 5, (0, 255, 0), -1)
                status = f"Tracking {detector.name}: {error} px"
            else:
                status = f"Confirming {detector.name} / holding position"
            cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (0, 255, 0), 2)
            if on_target is not None:
                on_target(*error)

            cv2.imshow(window, frame)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                break
            if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        try:
            camera.release()
        finally:
            cv2.destroyAllWindows()
