import io
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch


class StopReceiver(Exception):
    pass


class Input(io.StringIO):
    def read(self, size):
        value = super().read(size)
        if not value:
            raise StopReceiver
        return value


class ReceiverTests(unittest.TestCase):
    def test_variable_counts_and_invalid_commands(self):
        for count in (2, 4, 5):
            motors = [SimpleNamespace(angle=None) for _ in range(count)]
            servo = SimpleNamespace(Servo=Mock(side_effect=motors))
            modules = {
                "supervisor": SimpleNamespace(runtime=SimpleNamespace(serial_bytes_available=True)),
                "pwmio": SimpleNamespace(PWMOut=Mock()),
                "adafruit_motor": SimpleNamespace(servo=servo),
            }
            valid = ",".join(str(70 + i) for i in range(count))
            invalid = ["bad", "90", ",".join(["130"] * count), ",".join(["nan"] * count)]
            data = valid + "\n" + "\n".join(invalid) + "\n"
            with patch.dict("sys.modules", modules), patch("sys.stdin", Input(data)):
                namespace = {}
                with open(Path(__file__).resolve().parents[1] / "pico" / "pico_receiver.py") as source:
                    exec(compile(source.read(), "pico_receiver.py", "exec"), namespace)
                with self.assertRaises(StopReceiver):
                    namespace["run"](tuple(range(count)))
            self.assertEqual([motor.angle for motor in motors], list(range(70, 70 + count)))


if __name__ == "__main__":
    unittest.main()

