import os
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_DIR / "models" / "yolo26n.pt"
CONFIDENCE = 0.5


class ObjectDetector:
    def __init__(self, excluded_names=("person", "chair", "backpack")):
        os.environ.setdefault("YOLO_CONFIG_DIR", str(PROJECT_DIR / ".yolo"))
        os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_DIR / ".yolo" / "matplotlib"))
        from ultralytics import YOLO

        self.model = YOLO(str(MODEL_PATH))
        self.classes = [i for i, name in self.model.names.items() if name not in excluded_names]

    def detect(self, frame):
        self.result = self.model(frame, classes=self.classes, conf=CONFIDENCE, verbose=False)[0]
        if self.result.boxes is None:
            return []
        return sorted({self.result.names[int(i)] for i in self.result.boxes.cls.tolist()})


def main():
    from classes import Robot

    return Robot().object_detection()


if __name__ == "__main__":
    main()
