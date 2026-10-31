# TC78H653FTG dual H-bridge, one brushed DC motor on OUT1/OUT2.
# Strap MODE and LARGE to GND (IN/IN input, Small mode). IN3/IN4 stay open
# (internal pulldown). STBY is active high; do not tie it to VM (input max 5.5 V).
#
# IN/IN, Small, STBY high:
#   IN1 PWM, IN2 low  -> forward (OUT1 high, OUT2 low)
#   IN1 low, IN2 PWM  -> reverse
#   both PWM, same duty -> short brake (channels of one slice are in phase)
#   both low          -> coast (Hi-Z)
# STBY low            -> outputs off
#
# drive / brake / coast do not raise STBY. Call enable() first.
from machine import Pin, PWM


def _duty_u16(value):
    if value <= 0:
        return 0
    if value >= 255:
        return 65535
    return value * 65535 // 255


class TC78H653FTG:
    def __init__(self, in1, in2, stby, freq_hz=20000):
        # Hold the chip in standby until both inputs are driven low.
        self._stby = Pin(stby, Pin.OUT, value=0)
        self._in1 = PWM(Pin(in1))
        self._in2 = PWM(Pin(in2))
        self._in1.freq(freq_hz)
        self._in1.duty_u16(0)
        self._in2.duty_u16(0)

    def enable(self):
        self._stby.value(1)

    def drive(self, value):
        """Signed speed, -255..255. Positive is forward. 0 coasts. Does not change STBY.

        The idle input is cleared before the active one is raised, so a direction
        change does not pass through both-high (short brake).
        """
        if value > 255:
            value = 255
        elif value < -255:
            value = -255
        if value > 0:
            self._in2.duty_u16(0)
            self._in1.duty_u16(_duty_u16(value))
        elif value < 0:
            self._in1.duty_u16(0)
            self._in2.duty_u16(_duty_u16(-value))
        else:
            self._in1.duty_u16(0)
            self._in2.duty_u16(0)

    def brake(self, value=255):
        """Short brake, 0..255. 255 holds both inputs high. Does not change STBY."""
        if value < 0:
            value = 0
        elif value > 255:
            value = 255
        duty = _duty_u16(value)
        self._in1.duty_u16(duty)
        self._in2.duty_u16(duty)

    def coast(self):
        """Both inputs low. STBY stays where it is."""
        self._in1.duty_u16(0)
        self._in2.duty_u16(0)

    def standby(self):
        """Inputs low, then STBY low. A low-to-high on STBY also clears an overcurrent latch."""
        self.coast()
        self._stby.value(0)

    def deinit(self):
        self.standby()
        self._in1.deinit()
        self._in2.deinit()
