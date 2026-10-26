import cv2
from face_target import StableFaceTarget

def main(on_face=None, camera_index=0, source="percipio"):
    face_detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    if source == "percipio":
        from percipio_camera import PercipioCamera
        camera = PercipioCamera()
    elif source == "webcam":
        camera = cv2.VideoCapture(camera_index)
    else:
        raise ValueError(f"Unknown camera source: {source}")
    tracker = StableFaceTarget()
    window_name = "Face detection - press Q to quit"
    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError(f"Cannot read {source} camera. Close other camera apps and check the connection.")
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_detector.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=8, minSize=(50, 50))
            frame_height, frame_width = frame.shape[:2]
            center_x, center_y = frame_width // 2, frame_height // 2
            cv2.circle(frame, (center_x, center_y), 5, (255, 255, 0), -1)
            cv2.putText(frame, "(0, 0)", (center_x + 10, center_y + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

            # Only a confirmed, consistent target can steer the head.
            for x, y, width, height in faces:
                cv2.rectangle(frame, (x, y), (x + width, y + height), (100, 100, 100), 1)
            point = tracker.update(faces)
            target = None
            if point is not None:
                face_x, face_y = map(round, point)
                target = (face_x - center_x, center_y - face_y)
                cv2.circle(frame, (face_x, face_y), 5, (0, 255, 0), -1)
                cv2.putText(frame, f"Tracking: {target} px", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "Confirming face / holding position", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)

            if on_face is not None:
                on_face(*(target if target is not None else (None, None)),
                        frame_width=frame_width, frame_height=frame_height)

            cv2.imshow(window_name, frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    from Communicate_pico import main as run

    run()


