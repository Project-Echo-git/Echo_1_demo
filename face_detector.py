import cv2


class FaceDetector:
    name = "face"
    target_point = (0.47, 0.3)

    def __init__(self):
        self.model = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        if self.model.empty():
            raise RuntimeError("Could not load the OpenCV face detector.")

    def detect(self, frame):
        """Return bounding boxes as (x, y, width, height)."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return self.model.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=8, minSize=(50, 50)
        )
