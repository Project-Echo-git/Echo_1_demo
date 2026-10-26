import unittest
from unittest.mock import patch

from send_to_pico import Pico, send_angles
from classes import PICOS


class PicoTests(unittest.TestCase):
    def test_routing_and_variable_angle_counts(self):
        for count in (2, 4, 5):
            pico = Pico("test_pico", range(count), "COM8")
            with patch.dict(PICOS, {"test_part": pico}), patch("serial.Serial") as serial:
                try:
                    send_angles("test_part", *range(90, 90 + count))
                    send_angles("test_part", *range(90, 90 + count))
                    serial.assert_called_once_with("COM8", 115200, timeout=1, write_timeout=1)
                    expected = (",".join(f"{angle:.2f}" for angle in range(90, 90 + count)) + "\n").encode()
                    self.assertEqual(serial.return_value.write.call_args.args, (expected,))
                finally:
                    pico.close()
                serial.return_value.close.assert_called_once()

    def test_invalid_angles_do_not_open_serial(self):
        pico = Pico("left_pico", (28, 19), "COM4")
        with patch("serial.Serial") as serial:
            for angles in ((90,), (90, 90, 90), (float("nan"), 90), (90, float("inf"))):
                with self.assertRaises(ValueError):
                    pico.send_angles(*angles)
            serial.assert_not_called()

    def test_unknown_part_does_not_open_serial(self):
        with patch("serial.Serial") as serial:
            with self.assertRaises(KeyError):
                send_angles("missing", 90, 90)
            serial.assert_not_called()


if __name__ == "__main__":
    unittest.main()
