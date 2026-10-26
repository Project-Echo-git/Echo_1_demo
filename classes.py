import time
from contextlib import nullcontext

import cv2
from send_to_pico import Pico

PICOS = {
    "neck": Pico("left_pico", pins=(28, 19)),
}


class Arm:
    def __init__(self, length, dof, J1, J2, J3, J4, J5):
        self.length = length
        self.dof = dof
        self.J1 = J1
        self.J2 = J2 
        self.J3 = J3
        self.J4 = J4
        self.J5 = J5


class Hand:
    
    def __init__(self, servo_thumb, servo_fingers):
        self.thumb = servo_thumb
        self.fingers = servo_fingers

    def close(self):
        return f"Closing hand with {self.fingers} and {self.thumb}"
    def open(self):
        return f"Opening hand with {self.fingers} and {self.thumb}"


class Neck:
    def __init__(self, pitch, yaw):
        self.pitch = pitch
        self.yaw = yaw

class Robot:
    def __init__(self, model=None, year=None, source="percipio", camera_index=0,
                 port=None, dry_run=False, debug_timing=False):
        self.model = model
        self.year = year
        self.source = source
        self.camera_index = camera_index
        self.dry_run = dry_run
        self.debug_timing = debug_timing
        self.picos = PICOS
        if port is not None and not dry_run:
            self.picos["neck"].port = port
        self.left_arm = Arm(1.0, 5, "D28", "D29", "D30", "D31", "D32")
        self.right_arm = Arm(1.0, 5, "D5", "D6", "D7", "D9", "D12")
        self.left_hand = Hand("D4", "D9")
        self.right_hand = Hand("D10", "D11")
        self.neck = Neck(pitch=19, yaw=28)

    def track_face(self):
        from face_tracker import FaceTracker

        return self._track(FaceTracker())

    def track_person(self):
        from person_tracker import PersonTracker

        return self._track(PersonTracker())

    def _track(self, tracker):
        from center_pixel_PID import TargetController

        connection = nullcontext(None) if self.dry_run else self.picos["neck"]
        with connection as pico:
            controller = TargetController(pico, debug_timing=self.debug_timing)
            if pico is not None:
                pico.send_angles(controller.angle_x, controller.angle_y)
                print(f"Sending servo angles to {pico.port}. Press Q to stop.")
            run_tracking(tracker, source=self.source, camera_index=self.camera_index,
                         on_target=controller.update)

    def object_detection(self, on_objects=None):
        from object_detection import ObjectDetector

        detector = ObjectDetector()
        camera = open_camera(self.source, self.camera_index)
        previous_names = []
        names = []
        try:
            while True:
                ok, frame = camera.read()
                if not ok:
                    raise RuntimeError("Cannot read camera.")
                names = detector.detect(frame)
                if on_objects is not None:
                    on_objects(names)
                elif names != previous_names:
                    print(", ".join(names), flush=True)
                previous_names = names
                cv2.imshow("Objects - Q to quit", detector.result.plot())
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

    def non_verbal_no(self):
        self._neck_gesture(0)

    def non_verbal_yes(self):
        self._neck_gesture(1)

    def _neck_gesture(self, axis):
        connection = nullcontext(None) if self.dry_run else self.picos["neck"]
        with connection as pico:
            for angle in (*range(90, 59, -5), *range(65, 121, 5), *range(115, 89, -5)):
                angles = [90, 90]
                angles[axis] = angle
                if pico is not None:
                    pico.send_angles(*angles)
                else:
                    print(tuple(angles))
                time.sleep(0.05)

    def wave_left(self):
        raise NotImplementedError("Configure the left arm Pico and wave angles first.")


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
