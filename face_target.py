"""Confirm and smooth face targets before steering the moving camera."""
import math
import time

class StableFaceTarget:
    POINT_X = 0.47
    POINT_Y = 0.3

    def __init__(self):
        self.box = None
        self.count = 0
        self.confirmed = False
        self.point = None
        self.last_seen = None
        self.started = None

    def update(self, faces, now=None):
        now = time.monotonic() if now is None else now
        faces = [tuple(map(float, face)) for face in faces]
        if self.last_seen is not None and now - self.last_seen > 0.5:
            self.__init__()
        selected = None
        if self.box is not None:
            x, y, w, h = self.box
            matches = []
            for candidate in faces:
                cx, cy, cw, ch = candidate
                distance = math.hypot(cx + cw / 2 - x - w / 2, cy + ch / 2 - y - h / 2)
                if (0.65 <= cw / w <= 1.55 and 0.65 <= ch / h <= 1.55
                        and distance <= 0.6 * max(w, h)):
                    matches.append((distance, candidate))
            if matches:
                selected = min(matches, key=lambda item: item[0])[1]
        elif faces:
            selected = max(faces, key=lambda box: box[2] * box[3])
        if selected is None:
            # No stale steering commands; briefly retain the confirmed identity.
            if not self.confirmed:
                self.__init__()
            self.point = None
            return None
        dt = 0 if self.last_seen is None else now - self.last_seen
        if self.started is None:
            self.started = now
        self.box = selected
        self.last_seen = now
        self.count += 1
        self.confirmed = self.confirmed or (self.count >= 4 and now - self.started >= 0.15)
        if not self.confirmed:
            return None
        x, y, w, h = selected
        point = (x + w * self.POINT_X, y + h * self.POINT_Y)
        if self.point is not None:
            alpha = 1 - math.exp(-max(dt, 0) / 0.08)
            point = tuple(old + alpha * (new - old) for old, new in zip(self.point, point))
        self.point = point
        return point
