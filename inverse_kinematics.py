class InverseKinematicsController:
    def __init__(self, pico=None):
        self.pico = pico

    def solve(self, x, y, z):
        raise NotImplementedError("Set the arm geometry and calculate servo angles here.")

    def update(self, x, y, z):
        angles = self.solve(x, y, z)
        if self.pico is not None:
            self.pico.send_angles(*angles)
        return angles
