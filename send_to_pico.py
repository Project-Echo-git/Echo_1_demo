import math

BAUD_RATE = 115200


def find_pico_port():
    from serial.tools import list_ports

    ports = [p.device for p in list_ports.comports() if p.vid in (0x2E8A, 0x239A)]
    if len(ports) != 1:
        raise RuntimeError("Set the Pico port or pass --port.")
    return ports[0]


class Pico:
    def __init__(self, name, pins, port=None):
        self.name = name
        self.pins = tuple(pins)
        self.port = port
        self.serial = None

    def open(self):
        import serial

        if self.serial is None:
            self.port = self.port or find_pico_port()
            self.serial = serial.Serial(self.port, BAUD_RATE, timeout=1, write_timeout=1)
        return self

    def send_angles(self, *angles):
        if len(angles) != len(self.pins):
            raise ValueError(f"{self.name} needs {len(self.pins)} angles.")
        if not all(math.isfinite(angle) for angle in angles):
            raise ValueError("Angles must be finite numbers.")
        command = ",".join(f"{angle:.2f}" for angle in angles) + "\n"
        self.open()
        self.serial.write(command.encode("ascii"))

    def close(self):
        if self.serial is not None:
            self.serial.close()
            self.serial = None

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


PICOS = {
    "left_arm": Pico("left_pico", pins=(28, 19)),
}


def send_angles(part, *angles):
    PICOS[part].send_angles(*angles)
