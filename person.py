import os
from pathlib import Path

import cv2
from face_target import StableFaceTarget

PROJECT_DIR = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_DIR / 'models' / 'yolo26n.pt'
CONFIDENCE = 0.65
IMAGE_SIZE = 640


class StablePersonTarget(StableFaceTarget):
    POINT_X = 0.5
    POINT_Y = 0.25


def load_model():
    os.environ.setdefault('YOLO_CONFIG_DIR', str(PROJECT_DIR / '.yolo'))
    os.environ.setdefault('MPLCONFIGDIR', str(PROJECT_DIR / '.yolo' / 'matplotlib'))
    from ultralytics import YOLO
    MODEL_PATH.parent.mkdir(exist_ok=True)
    return YOLO(str(MODEL_PATH))


def main(on_face=None, camera_index=0, source='percipio'):
    # on_face is the shared controller callback: x/y pixel errors and image size.
    model = load_model()
    tracker = StablePersonTarget()
    if source == 'percipio':
        from percipio_camera import PercipioCamera
        camera = PercipioCamera()
    elif source == 'webcam':
        camera = cv2.VideoCapture(camera_index)
    else:
        raise ValueError(f'Unknown camera source: {source}')
    window = 'YOLO26 person tracking - Q to quit'
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError(f'Cannot read {source} camera.')
            result = model.predict(frame, classes=[0], conf=CONFIDENCE,
                                   imgsz=IMAGE_SIZE, verbose=False)[0]
            candidates = []
            if result.boxes is not None:
                for box, score in zip(result.boxes.xyxy.cpu().numpy(),
                                      result.boxes.conf.cpu().numpy()):
                    x1, y1, x2, y2 = map(float, box)
                    width, height = x2-x1, y2-y1
                    if width <= 0 or height <= 0:
                        continue
                    candidates.append((x1, y1, width, height))
                    cv2.rectangle(frame, (round(x1), round(y1)),
                                  (round(x2), round(y2)), (255, 180, 0), 2)
                    # Exact requested point on each detected person's box.
                    dot = (round(x1 + width * 0.5), round(y1 + height * 0.25))
                    cv2.circle(frame, dot, 6, (0, 255, 255), -1)
                    cv2.putText(frame, f'person {score:.2f}',
                                (round(x1), max(20, round(y1)-8)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 180, 0), 2)
            point = tracker.update(candidates)
            height, width = frame.shape[:2]
            cx, cy = width // 2, height // 2
            cv2.drawMarker(frame, (cx, cy), (255, 255, 0), cv2.MARKER_CROSS, 16, 2)
            target = None
            if point is not None:
                # Use the smoothed point for steering, retaining false-positive protection.
                target = (round(point[0]-cx), round(cy-point[1]))
                x, y, w, h = tracker.box
                cv2.rectangle(frame, (round(x), round(y)), (round(x+w), round(y+h)),
                              (0, 255, 0), 3)
                status = f'Tracking person: {target} px'
            else:
                status = 'Confirming person / holding position'
            cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (0, 255, 0), 2)
            if on_face is not None:
                on_face(*(target if target is not None else (None, None)),
                        frame_width=width, frame_height=height)
            cv2.imshow(window, frame)
            if cv2.waitKey(1) & 0xff in (ord('q'), 27):
                break
            if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    from Communicate_pico import main as run_tracking
    run_tracking(track_face=main)

