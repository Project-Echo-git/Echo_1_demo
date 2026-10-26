import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

import launch
import classes as tracking
from center_pixel_PID import TargetController
from face_tracker import FaceTracker
from person_tracker import PersonTracker
from send_to_pico import Pico, send_angles
from classes import PICOS
from face_tracker import StableTarget


class TargetTests(unittest.TestCase):
    def test_confirmation_loss_and_reacquisition_preserve_aim_point(self):
        tracker = StableTarget(0.5, 0.25)
        box = [(100, 100, 80, 160)]
        for now in (0, 0.05, 0.1):
            self.assertIsNone(tracker.update(box, now=now))
        self.assertEqual(tracker.update(box, now=0.2), (140, 140))
        self.assertIsNone(tracker.update([], now=0.25))
        self.assertIsNone(tracker.update([], now=1.0))
        for now in (1.1, 1.15, 1.2):
            self.assertIsNone(tracker.update(box, now=now))
        self.assertEqual(tracker.update(box, now=1.3), (140, 140))

    def test_controller_limits_and_target_loss(self):
        pico = Mock()
        controller = TargetController(pico)
        with patch("center_pixel_PID.time.monotonic", side_effect=[i * 0.033 for i in range(400)]):
            for error in (10000, -10000):
                for _ in range(200):
                    controller.update(error, error)
        angles = [call.args for call in pico.send_angles.call_args_list]
        self.assertTrue(all(60 <= x <= 120 and 60 <= y <= 120 for x, y in angles))
        for axis in (0, 1):
            self.assertEqual(min(a[axis] for a in angles), 60)
            self.assertEqual(max(a[axis] for a in angles), 120)
        previous = (controller.angle_x, controller.angle_y)
        count = pico.send_angles.call_count
        controller.update(None, None)
        self.assertEqual((controller.angle_x, controller.angle_y), previous)
        self.assertEqual(pico.send_angles.call_count, count)


class DetectorTests(unittest.TestCase):
    def test_face_tracker_on_blank_image(self):
        boxes = FaceTracker().detect(np.zeros((240, 320, 3), dtype=np.uint8))
        self.assertEqual(len(boxes), 0)

    def test_person_boxes_and_filter(self):
        detector = PersonTracker.__new__(PersonTracker)
        detector.model = Mock()
        xyxy = Mock()
        xyxy.cpu.return_value.numpy.return_value = np.array([
            [10, 20, 70, 120], [30, 30, 20, 40]
        ])
        detector.model.predict.return_value = [SimpleNamespace(boxes=SimpleNamespace(xyxy=xyxy))]
        self.assertEqual(detector.detect(None), [(10.0, 20.0, 60.0, 100.0)])
        self.assertEqual(detector.model.predict.call_args.kwargs["classes"], [0])
        detector.model.predict.return_value = [SimpleNamespace(boxes=None)]
        self.assertEqual(detector.detect(None), [])


class TrackingTests(unittest.TestCase):
    def gui(self, stack, wait_keys):
        for method in ("drawMarker", "rectangle", "circle", "putText", "imshow"):
            stack.enter_context(patch.object(tracking.cv2, method))
        stack.enter_context(patch.object(tracking.cv2, "waitKey", side_effect=wait_keys))
        stack.enter_context(patch.object(tracking.cv2, "getWindowProperty", return_value=1))
        return stack.enter_context(patch.object(tracking.cv2, "destroyAllWindows"))

    def test_both_detectors_use_same_loop_and_loss_callback(self):
        for name, aim, expected in (
            ("face", (0.47, 0.3), (18, 0)),
            ("person", (0.5, 0.25), (20, 10)),
        ):
            with self.subTest(detector=name), ExitStack() as stack:
                camera = Mock()
                camera.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
                detector = Mock(name=name)
                detector.name, detector.target_point = name, aim
                detector.detect.side_effect = [[(300, 180, 80, 200)]] * 4 + [[]]
                detector.target = StableTarget(*aim)
                cls = FaceTracker if name == "face" else PersonTracker
                detector.update = lambda frame: cls.update(detector, frame)
                stack.enter_context(patch.object(tracking, "open_camera", return_value=camera))
                stack.enter_context(patch("face_tracker.time.monotonic", side_effect=[0, .05, .1, .2, .25]))
                cleanup = self.gui(stack, [-1] * 4 + [ord("q")])
                callback = Mock()
                tracking.run_tracking(detector, source="webcam", on_target=callback)
                self.assertEqual([c.args for c in callback.call_args_list],
                                 [(None, None)] * 3 + [expected, (None, None)])
                camera.release.assert_called_once()
                cleanup.assert_called_once()

    def test_cleanup_after_read_detector_or_callback_failure(self):
        for failure in ("read", "detect", "callback"):
            with self.subTest(failure=failure), ExitStack() as stack:
                camera = Mock()
                camera.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
                detector = Mock()
                detector.name, detector.target_point = "face", (0.47, 0.3)
                detector.detect.return_value = []
                detector.target_point = (0.47, 0.3)
                detector.target = StableTarget(*detector.target_point)
                detector.update = lambda frame: FaceTracker.update(detector, frame)
                callback = Mock()
                if failure == "read":
                    camera.read.return_value = (False, None)
                elif failure == "detect":
                    detector.detect.side_effect = RuntimeError("detector failed")
                else:
                    callback.side_effect = RuntimeError("serial failed")
                stack.enter_context(patch.object(tracking, "open_camera", return_value=camera))
                cleanup = self.gui(stack, [])
                with self.assertRaises(RuntimeError):
                    tracking.run_tracking(detector, on_target=callback)
                camera.release.assert_called_once()
                cleanup.assert_called_once()

    def test_unavailable_webcam_is_released(self):
        with patch.object(tracking.cv2, "VideoCapture") as capture:
            capture.return_value.isOpened.return_value = False
            with self.assertRaises(RuntimeError):
                tracking.open_camera("webcam", 2)
            capture.assert_called_once_with(2)
            capture.return_value.release.assert_called_once()


class ConnectionAndLaunchTests(unittest.TestCase):
    def test_serial_format_and_close_on_error(self):
        with patch("serial.Serial") as serial:
            with self.assertRaisesRegex(RuntimeError, "tracking failed"):
                with Pico("left_pico", (28, 19), "COM4") as pico:
                    pico.send_angles(90, 60.125)
                    raise RuntimeError("tracking failed")
            serial.return_value.write.assert_called_once_with(b"90.00,60.12\n")
            serial.return_value.close.assert_called_once()

    def test_preview_routes_detector_without_opening_serial(self):
        for name, module, cls in (("face", "face_tracker", "FaceTracker"),
                                  ("person", "person_tracker", "PersonTracker")):
            with self.subTest(detector=name), patch(f"{module}.{cls}") as detector, \
                    patch.object(PICOS["neck"], "open") as pico, \
                    patch("classes.run_tracking") as loop:
                args = launch.parse_args(["--detector", name, "--source", "webcam",
                                          "--camera", "2", "--dry-run"])
                launch.run(args)
                pico.assert_not_called()
                self.assertIs(loop.call_args.args[0], detector.return_value)
                self.assertEqual(loop.call_args.kwargs["source"], "webcam")
                self.assertEqual(loop.call_args.kwargs["camera_index"], 2)
                self.assertIsNone(loop.call_args.kwargs["on_target"].__self__.pico)

    def test_launcher_closes_serial_when_tracking_fails(self):
        with patch("face_tracker.FaceTracker"), patch("serial.Serial") as serial, \
                patch("classes.run_tracking", side_effect=RuntimeError("camera failed")):
            with self.assertRaisesRegex(RuntimeError, "camera failed"):
                launch.run(launch.parse_args(["--port", "COM4"]))
            serial.return_value.write.assert_called_once_with(b"90.00,90.00\n")
            serial.return_value.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()




