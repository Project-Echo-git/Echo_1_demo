from person_detection import main as person
from obect_detection import main as ob
import send_to_pico


class Arm:
    def __init__(self, length, dof, J1, J2, J3, J4, J5):
        # here we fill in the amount of DOf and the pins for the servos
        self.length = length
        self.dof = dof
        self.J1 = J1
        self.J2 = J2 
        self.J3 = J3
        self.J4 = J4
        self.J5 = J5


class Hand:
    
    def __init__(self, servo_thumb, servo_fingers):
        # these are the pins for the pico per finger
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
    def __init__(self, model, year):
        self.model = model
        self.year = year
        self.left_arm = Arm(length=1.0, dof=5, J1= "D28", J2="D29", J3="D30", J4="D31", J5="D32")
        self.right_arm = Arm(length=1.0, dof=5, J1= "D5", J2="D6", J3="D7", J4="D9", J5="D12")
        self.left_hand = Hand(servo_thumb="D4", servo_fingers= "D9")
        self.right_hand = Hand(servo_thumb="D10", servo_fingers= "D11")
        self.neck = Neck(pitch="D28", yaw="D19")

    def object_detection(self):
        print(f"looking for the object")
        return ob.main()

    def non_verbal_no(self):
        for yaw in range(60,120,5):
            self.neck.yaw = yaw
            send_to_pico.send_angles(yaw)
        for yaw in range(120,60,-5):
            self.neck.yaw = yaw
            send_to_pico.send_angles(yaw)

    def non_verbal_yes(self):
        for pitch in range(60,120,5):
            self.neck.pitch = pitch
            send_to_pico.send_angles(pitch)
        for pitch in range(120,60,-5):
            self.neck.pitch = pitch
            send_to_pico.send_angles(pitch)

    def wave_left(self):
        self.left_arm.J1 = 30
        self.left_arm.J2 = 90
        self.left_arm.J3 = 90
        for J4 in range(60,120,5):
            self.neck.yaw = J4
            send_to_pico.send_angles(J4)
        for J4 in range(120,60,-5):
            self.neck.yaw = J4
            send_to_pico.send_angles(J4)






    


