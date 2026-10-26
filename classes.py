from contextlib import nullcontext

from send_to_pico import Pico
from neck_gestures import neck_gesture

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
            tracker.run(source=self.source, camera_index=self.camera_index,
                         on_target=controller.update)

    def object_detection(self, on_objects=None):
        from object_detection import ObjectDetector

        return ObjectDetector().run(source=self.source, camera_index=self.camera_index,
                                    on_objects=on_objects)

    def non_verbal_no(self):
        return neck_gesture(None if self.dry_run else self.picos["neck"], 0)

    def non_verbal_yes(self):
        return neck_gesture(None if self.dry_run else self.picos["neck"], 1)

    def wave_left(self):
        raise NotImplementedError("Configure the left arm Pico and wave angles first.")
