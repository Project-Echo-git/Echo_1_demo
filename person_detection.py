import os
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_DIR / "models" / "yolo26n.pt"
CONFIDENCE = 0.65
IMAGE_SIZE = 640


class PersonDetector:
    name = "person"
    target_point = (0.5, 0.25)

    def __init__(self):
        os.environ.setdefault("YOLO_CONFIG_DIR", str(PROJECT_DIR / ".yolo"))
        os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_DIR / ".yolo" / "matplotlib"))
        from ultralytics import YOLO

        self.model = YOLO(str(MODEL_PATH))

    def detect(self, frame):
        """Return bounding boxes as (x, y, width, height)."""
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
