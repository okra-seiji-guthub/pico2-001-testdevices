# roll / pitch estimate: complementary filter of accelerometer and gyro.
# Pure math (no machine import) so it also runs on a PC.
#   accel -> absolute but noisy while accelerating / cornering
#   gyro  -> smooth but drifts when integrated
# yaw is not estimated (no magnetometer, it would only drift).
import math

_RAD2DEG = 180.0 / math.pi

DT_MIN = 0.001
DT_MAX = 0.05
G_MIN = 0.8   # trust the accelerometer only while |a| is near 1 g
G_MAX = 1.2


class Attitude:
    def __init__(self, alpha=0.98, roll_sign=1, pitch_sign=1):
        self.alpha = alpha
        self.roll_sign = roll_sign
        self.pitch_sign = pitch_sign
        self.roll = 0.0     # deg
        self.pitch = 0.0    # deg
        self._ready = False

    def update(self, ax, ay, az, gx, gy, dt):
        """ax/ay/az in g, gx/gy in dps, dt in seconds."""
        if dt < DT_MIN:
            dt = DT_MIN
        elif dt > DT_MAX:
            dt = DT_MAX

        accel_roll = math.atan2(ay, az) * _RAD2DEG * self.roll_sign
        accel_pitch = math.atan2(-ax, math.sqrt(ay * ay + az * az)) * _RAD2DEG * self.pitch_sign

        if not self._ready:
            self.roll = accel_roll
            self.pitch = accel_pitch
            self._ready = True
            return

        g2 = ax * ax + ay * ay + az * az
        trust = G_MIN * G_MIN <= g2 <= G_MAX * G_MAX
        a = self.alpha if trust else 1.0   # a == 1.0: gyro only
        self.roll = a * (self.roll + gx * self.roll_sign * dt) + (1.0 - a) * accel_roll
        self.pitch = a * (self.pitch + gy * self.pitch_sign * dt) + (1.0 - a) * accel_pitch
