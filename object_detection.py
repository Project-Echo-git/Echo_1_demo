import cv2
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


    def run(self, source="percipio", camera_index=0, on_objects=None):
        camera = open_camera(source, camera_index)
        previous_names = []
        names = []
        try:
            while True:
                ok, frame = camera.read()
                if not ok:
                    raise RuntimeError("Cannot read camera.")
                names = self.detect(frame)
                if on_objects is not None:
                    on_objects(names)
                elif names != previous_names:
                    print(", ".join(names), flush=True)
                previous_names = names
                cv2.imshow("Objects - Q to quit", self.result.plot())
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    break
                if cv2.getWindowProperty("Objects - Q to quit", cv2.WND_PROP_VISIBLE) < 1:
                    break
        finally:
            try:
                camera.release()
            finally:
                cv2.destroyAllWindows()
        return names



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



def main():
    from classes import Robot

    return Robot().detect_objects()


if __name__ == "__main__":
    main()
