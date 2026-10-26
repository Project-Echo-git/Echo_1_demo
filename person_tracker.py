import math
import time
import os
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_DIR / "models" / "yolo26n.pt"
CONFIDENCE = 0.65
IMAGE_SIZE = 640


class PersonTracker:
    name = "person"
    target_point = (0.5, 0.25)

    def __init__(self):
        self.target = StableTarget(*self.target_point)
        os.environ.setdefault("YOLO_CONFIG_DIR", str(PROJECT_DIR / ".yolo"))
        os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_DIR / ".yolo" / "matplotlib"))
        from ultralytics import YOLO

        self.model = YOLO(str(MODEL_PATH))

    def detect(self, frame):
        result = self.model.predict(
            frame, classes=[0], conf=CONFIDENCE, imgsz=IMAGE_SIZE, verbose=False
        )[0]
        boxes = []
        if result.boxes is not None:
            for x1, y1, x2, y2 in result.boxes.xyxy.cpu().numpy():
                width, height = float(x2 - x1), float(y2 - y1)
                if width > 0 and height > 0:
                    boxes.append((float(x1), float(y1), width, height))
        return boxes

    def update(self, frame):
        self.boxes = self.detect(frame)
        self.point = self.target.update(self.boxes)
        self.box = self.target.box
        if self.point is None:
            return None, None
        height, width = frame.shape[:2]
        x, y = map(round, self.point)
        return x - width // 2, height // 2 - y


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
