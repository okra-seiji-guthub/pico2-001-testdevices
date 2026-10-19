# LSM6DSV16X accelerometer / gyroscope driver for MicroPython.
# Register map and scale factors follow ST DS13476:
# https://www.st.com/resource/en/datasheet/lsm6dsv16x.pdf

import time

_WHO_AM_I_REG = 0x0F
_WHO_AM_I = 0x70
_CTRL1 = 0x10
_CTRL2 = 0x11
_CTRL3 = 0x12
_CTRL6 = 0x15
_CTRL8 = 0x17
_OUT_TEMP_L = 0x20
_STATUS_REG = 0x1E
_STATUS_XLDA = 0x01
_STATUS_GDA = 0x02

_CTRL3_BDU = 0x40
_CTRL3_IF_INC = 0x04
_CTRL3_SW_RESET = 0x01

# ODR field for high-performance mode (OP_MODE = 000). 1.875 Hz is accelerometer only.
_ODR_CODES = (
    (1.875, 0x1),
    (7.5, 0x2),
    (15, 0x3),
    (30, 0x4),
    (60, 0x5),
    (120, 0x6),
    (240, 0x7),
    (480, 0x8),
    (960, 0x9),
    (1920, 0xA),
    (3840, 0xB),
    (7680, 0xC),
)

# Full-scale code, then g or dps per raw LSB.
_ACCEL_FS = {
    2: (0x00, 0.061 / 1000),
    4: (0x01, 0.122 / 1000),
    8: (0x02, 0.244 / 1000),
    16: (0x03, 0.488 / 1000),
}
_GYRO_FS = {
    125: (0x00, 4.375 / 1000),
    250: (0x01, 8.75 / 1000),
    500: (0x02, 17.5 / 1000),
    1000: (0x03, 35.0 / 1000),
    2000: (0x04, 70.0 / 1000),
    4000: (0x0C, 140.0 / 1000),
}


def _i16(lo, hi):
    value = lo | (hi << 8)
    if value & 0x8000:
        value -= 0x10000
    return value


def _odr_code(hz, kind):
    for rate, code in _ODR_CODES:
        if hz == rate:
            if kind == "gyro" and code < 0x2:
                break
            return code
    raise ValueError("unsupported {} ODR: {}".format(kind, hz))


def decode_sample(raw, accel_lsb, gyro_lsb):
    """Turn the 14-byte block at OUT_TEMP_L into g, dps, and degrees C."""
    if len(raw) != 14:
        raise ValueError("expected 14 bytes from OUT_TEMP_L")
    temp = _i16(raw[0], raw[1]) / 256 + 25
    gyro = (
        _i16(raw[2], raw[3]) * gyro_lsb,
        _i16(raw[4], raw[5]) * gyro_lsb,
        _i16(raw[6], raw[7]) * gyro_lsb,
    )
    accel = (
        _i16(raw[8], raw[9]) * accel_lsb,
        _i16(raw[10], raw[11]) * accel_lsb,
        _i16(raw[12], raw[13]) * accel_lsb,
    )
    return accel, gyro, temp


class LSM6DSV16X:
    def __init__(self, i2c, address=0x6A, accel_odr=120, gyro_odr=120, accel_fs=4, gyro_fs=2000):
        self.i2c = i2c
        self.address = address
        who = self._read(_WHO_AM_I_REG, 1)[0]
        if who != _WHO_AM_I:
            raise RuntimeError("LSM6DSV16X not found at 0x{:02X} (WHO_AM_I=0x{:02X})".format(address, who))

        accel_code, self._accel_lsb = _ACCEL_FS[accel_fs]
        gyro_code, self._gyro_lsb = _GYRO_FS[gyro_fs]
        accel_odr_code = _odr_code(accel_odr, "accel")
        gyro_odr_code = _odr_code(gyro_odr, "gyro")

        self._write(_CTRL3, _CTRL3_SW_RESET)
        for _ in range(20):
            time.sleep_ms(1)
            if not (self._read(_CTRL3, 1)[0] & _CTRL3_SW_RESET):
                break
        else:
            raise RuntimeError("LSM6DSV16X reset timed out")

        self._write(_CTRL3, _CTRL3_BDU | _CTRL3_IF_INC)
        self._write(_CTRL8, accel_code)
        self._write(_CTRL6, gyro_code)
        self._write(_CTRL1, accel_odr_code)
        self._write(_CTRL2, gyro_odr_code)
        self._wait_ready()

    def _write(self, reg, value):
        self.i2c.writeto_mem(self.address, reg, bytes([value & 0xFF]))

    def _read(self, reg, n):
        return self.i2c.readfrom_mem(self.address, reg, n)

    def read_accel(self):
        return self.read()["accel"]

    def read_gyro(self):
        return self.read()["gyro"]

    def read_temp(self):
        return self.read()["temp"]

    def _wait_ready(self, timeout_ms=50):
        for _ in range(timeout_ms):
            status = self._read(_STATUS_REG, 1)[0]
            if (status & (_STATUS_XLDA | _STATUS_GDA)) == (_STATUS_XLDA | _STATUS_GDA):
                return
            time.sleep_ms(1)
        raise RuntimeError("LSM6DSV16X data not ready")

    def read(self):
        self._wait_ready()
        raw = self._read(_OUT_TEMP_L, 14)
        accel, gyro, temp = decode_sample(raw, self._accel_lsb, self._gyro_lsb)
        return {"accel": accel, "gyro": gyro, "temp": temp}
