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
    def test_current_receiver_and_invalid_commands(self):
        for count in (2,):
            motors = [SimpleNamespace(angle=None) for _ in range(count)]
            servo = SimpleNamespace(Servo=Mock(side_effect=motors))
            modules = {
                "board": SimpleNamespace(GP28=28, GP19=19, GP18=18, GP17=17, GP16=16),
                "supervisor": SimpleNamespace(runtime=SimpleNamespace(serial_bytes_available=True)),
                "pwmio": SimpleNamespace(PWMOut=Mock()),
                "adafruit_motor": SimpleNamespace(servo=servo),
            }
            valid = ",".join(str(70 + i) for i in range(count))
            invalid = ["bad", "90", ",".join(["181"] * count), ",".join(["nan"] * count)]
            data = valid + "\n" + "\n".join(invalid) + "\n"
            with patch.dict("sys.modules", modules), patch("sys.stdin", Input(data)):
                namespace = {}
                with open(Path(__file__).resolve().parents[1] / "pico" / "pico_receiver.py") as source:
                    code = source.read()
                with self.assertRaises(StopReceiver):
                    exec(compile(code, "pico_receiver.py", "exec"), namespace)
            self.assertEqual([motor.angle for motor in motors], list(range(70, 70 + count)))


if __name__ == "__main__":
    unittest.main()



