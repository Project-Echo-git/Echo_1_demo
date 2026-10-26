from pathlib import Path
import time
import cv2
from ultralytics import YOLO
from percipio_camera import PercipioCamera


CONFIDENCE = 0.5


def main():
    model_path = Path(__file__).resolve().parent / "models" / "yolo26n.pt"
    model = YOLO(str(model_path))
    list = ["person", "chair", "backpack"]
    classes = [i for i, name in model.names.items() if name not in list]
    camera = PercipioCamera()
    previous_names = set()

    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError("Cannot read Percipio camera.")

            result = model(frame, classes=classes, conf=CONFIDENCE, verbose=False)[0]
            names = {result.names[int(i)] for i in result.boxes.cls.tolist()}
            # Print names only when the detected objects change.
            if names != previous_names:
                if names:
                    print(", ".join(sorted(names)), flush=True)
                previous_names = names

            cv2.imshow("Objects - Q to quit", result.plot())
            time.sleep(0.01)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                break
            if cv2.getWindowProperty("Objects - Q to quit", cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
