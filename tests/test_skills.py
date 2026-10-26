import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch

import classes
import launch
from center_pixel_PID import TargetController
from object_detection import ObjectDetector


class SkillTests(unittest.TestCase):
    def test_launch_selects_each_robot_skill(self):
        for skill in launch.SKILLS:
            with self.subTest(skill=skill), patch("classes.Robot") as robot:
                launch.run(launch.parse_args([skill]).skill)
                robot.assert_called_once_with()
                getattr(robot.return_value, skill).assert_called_once_with()

    def test_object_model_returns_unique_names(self):
        detector = ObjectDetector.__new__(ObjectDetector)
        detector.classes = [1, 2]
        detector.model = Mock()
        labels = Mock()
        labels.tolist.return_value = [2, 1, 2]
        detector.model.return_value = [SimpleNamespace(names={1: "cup", 2: "bottle"}, boxes=SimpleNamespace(cls=labels))]
        self.assertEqual(detector.detect(None), ["bottle", "cup"])
        detector.model.return_value = [SimpleNamespace(boxes=None)]
        self.assertEqual(detector.detect(None), [])

    def test_object_skill_selects_consistent_name_and_closes(self):
        cases = (
            ([["cup", "bottle"]] * 25 + [["cup"]] * 25, "cup"),
            ([["cup"]] * 24 + [["bottle"]] * 26, "bottle"),
            ([[]] * 50 + [["cup"]] * 25, "cup"),
            ([["cup"] * 25] + [[]] * 49, None),
            ([[]] * 50, None),
        )
        for frames, expected in cases:
            with self.subTest(frames=frames), ExitStack() as stack:
                model = stack.enter_context(patch("object_detection.ObjectDetector.detect", side_effect=frames))
                stack.enter_context(patch("object_detection.ObjectDetector.__init__", return_value=None))
                stack.enter_context(patch.object(ObjectDetector, "result", Mock(), create=True))
                camera = stack.enter_context(patch("object_detection.open_camera"))
                camera.return_value.read.return_value = (True, object())
                stack.enter_context(patch("object_detection.cv2.imshow"))
                stack.enter_context(patch("object_detection.cv2.waitKey", return_value=-1))
                stack.enter_context(patch("object_detection.cv2.getWindowProperty", return_value=1))
                times = [i * 0.1 for i in range(len(frames))]
                if expected is None:
                    times[-1] = 30.0
                stack.enter_context(patch("object_detection.time.monotonic", side_effect=times))
                cleanup = stack.enter_context(patch("object_detection.cv2.destroyAllWindows"))
                serial = stack.enter_context(patch("serial.Serial"))
                output = stack.enter_context(patch("builtins.print"))
                callback = Mock()
                self.assertEqual(classes.Robot().detect_objects(callback), expected)
                self.assertEqual(model.call_count, len(frames))
                output.assert_called_once_with(f"the detected object is: {expected if expected is not None else 'none'}", flush=True)
                if expected is None:
                    callback.assert_not_called()
                else:
                    callback.assert_called_once_with(expected)
                serial.assert_not_called()
                camera.return_value.release.assert_called_once()
                cleanup.assert_called_once()

    def test_object_cancellation_does_not_print_none(self):
        with ExitStack() as stack:
            stack.enter_context(patch("object_detection.ObjectDetector.__init__", return_value=None))
            stack.enter_context(patch("object_detection.ObjectDetector.detect", return_value=[]))
            stack.enter_context(patch.object(ObjectDetector, "result", Mock(), create=True))
            camera = stack.enter_context(patch("object_detection.open_camera"))
            camera.return_value.read.return_value = (True, object())
            stack.enter_context(patch("object_detection.cv2.imshow"))
            stack.enter_context(patch("object_detection.cv2.waitKey", return_value=ord("q")))
            cleanup = stack.enter_context(patch("object_detection.cv2.destroyAllWindows"))
            output = stack.enter_context(patch("builtins.print"))
            self.assertIsNone(classes.Robot().detect_objects())
            output.assert_not_called()
            camera.return_value.release.assert_called_once()
            cleanup.assert_called_once()

    def test_object_skill_cleans_up_on_failure(self):
        with patch("object_detection.ObjectDetector.__init__", return_value=None), patch("object_detection.ObjectDetector.detect") as model, patch("object_detection.open_camera") as camera, patch("object_detection.cv2.destroyAllWindows") as cleanup:
            camera.return_value.read.return_value = (True, object())
            model.side_effect = RuntimeError("failed")
            with self.assertRaises(RuntimeError):
                classes.Robot().detect_objects()
            camera.return_value.release.assert_called_once()
            cleanup.assert_called_once()

    def test_pid_returns_same_angles_it_sends(self):
        pico = Mock()
        angles = TargetController(pico).update(20, -10)
        pico.send_angles.assert_called_once_with(*angles)

    def test_neck_gestures_use_two_angles_and_close(self):
        for method, axis in (("shake_no", 0), ("nod_yes", 1)):
            with self.subTest(method=method), patch("serial.Serial") as serial, patch("neck_gestures.time.sleep"):
                robot = classes.Robot(port="COM4")
                getattr(robot, method)()
                commands = [tuple(map(float, call.args[0].decode().strip().split(","))) for call in serial.return_value.write.call_args_list]
                self.assertTrue(all(len(command) == 2 and command[1 - axis] == 90 for command in commands))
                self.assertEqual(commands[-1], (90, 90))
                self.assertTrue(all(60 <= angle <= 120 for command in commands for angle in command))
                serial.return_value.close.assert_called_once()


    def test_neck_gesture_dry_run_does_not_open_serial(self):
        with patch("serial.Serial") as serial, patch("neck_gestures.time.sleep"), patch("builtins.print") as output:
            robot = classes.Robot(dry_run=True)
            robot.nod_yes()
            robot.shake_no()
            serial.assert_not_called()
            self.assertEqual(output.call_args.args, ((90, 90),))

    def test_neck_gesture_closes_connection_after_send_failure(self):
        with patch("serial.Serial") as serial, patch("neck_gestures.time.sleep"):
            serial.return_value.write.side_effect = RuntimeError("send failed")
            with self.assertRaisesRegex(RuntimeError, "send failed"):
                classes.Robot(port="COM4").nod_yes()
            serial.return_value.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
