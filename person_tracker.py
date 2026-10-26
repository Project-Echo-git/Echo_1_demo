import cv2
from face_tracker import StableTarget


def open_camera(source, camera_index=0):
    if source == "percipio":
        from percipio_camera import PercipioCamera

        return PercipioCamera()
    if source == "webcam":
        camera = cv2.VideoCapture(camera_index)
        if not camera.isOpened():
            camera.release()
            raise RuntimeError(f"Cannot open webcam {camera_index}.")
        return camera
    raise ValueError(f"Unknown camera source: {source}")


def run_tracking(detector, source="percipio", camera_index=0, on_target=None):
    """Run detection and steering; always release the camera on exit."""
    tracker = StableTarget(*detector.target_point)
    window = f"{detector.name.capitalize()} tracking - Q to quit"
    camera = open_camera(source, camera_index)
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError(
                    f"Cannot read {source} camera. Close other camera apps and check the connection."
                )
            boxes = detector.detect(frame)
            point = tracker.update(boxes)
            height, width = frame.shape[:2]
            cx, cy = width // 2, height // 2
            cv2.drawMarker(frame, (cx, cy), (255, 255, 0), cv2.MARKER_CROSS, 16, 2)
            for x, y, w, h in boxes:
                cv2.rectangle(frame, (round(x), round(y)),
                              (round(x + w), round(y + h)), (100, 100, 100), 1)
                dot = (round(x + w * detector.target_point[0]),
                       round(y + h * detector.target_point[1]))
                cv2.circle(frame, dot, 4, (0, 255, 255), -1)

            error = (None, None)
            if point is not None:
                px, py = map(round, point)
                error = (px - cx, cy - py)
                x, y, w, h = tracker.box
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
