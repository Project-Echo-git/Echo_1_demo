from contextlib import nullcontext
import time

def neck_gesture(pico, axis):
    connection = nullcontext(None) if pico is None else pico
    with connection as pico:
        for angle in (*range(90, 59, -5), *range(65, 121, 5), *range(115, 89, -5)):
            angles = [90, 90]
            angles[axis] = angle
            if pico is not None:
                pico.send_angles(*angles)
            else:
                print(tuple(angles))
            time.sleep(0.05)
