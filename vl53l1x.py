# Source: OpenMV project (scripts/libraries/vl53l1x.py)
# https://github.com/openmv/openmv/blob/master/scripts/libraries/vl53l1x.py
import time

VL51L1X_DEFAULT_CONFIGURATION = bytes(
    [
        0x00,  # 0x2d : set bit 2 and 5 to 1 for fast plus mode (1MHz I2C), else don't touch
        0x00,  # 0x2e : bit 0 if I2C pulled up at 1.8V, else set bit 0 to 1 (pull up at AVDD)
        0x00,  # 0x2f : bit 0 if GPIO pulled up at 1.8V, else set bit 0 to 1 (pull up at AVDD)
        0x01,  # 0x30 : set bit 4 to 0 for active high interrupt and 1 for active low
               # (bits 3:0 must be 0x1), use SetInterruptPolarity()
        0x02,  # 0x31 : bit 1 = interrupt depending on the polarity, use CheckForDataReady()
        0x00,  # 0x32 : not user-modifiable
        0x02,  # 0x33 : not user-modifiable
        0x08,  # 0x34 : not user-modifiable
        0x00,  # 0x35 : not user-modifiable
        0x08,  # 0x36 : not user-modifiable
        0x10,  # 0x37 : not user-modifiable
        0x01,  # 0x38 : not user-modifiable
        0x01,  # 0x39 : not user-modifiable
        0x00,  # 0x3a : not user-modifiable
        0x00,  # 0x3b : not user-modifiable
        0x00,  # 0x3c : not user-modifiable
        0x00,  # 0x3d : not user-modifiable
        0xFF,  # 0x3e : not user-modifiable
        0x00,  # 0x3f : not user-modifiable
        0x0F,  # 0x40 : not user-modifiable
        0x00,  # 0x41 : not user-modifiable
        0x00,  # 0x42 : not user-modifiable
        0x00,  # 0x43 : not user-modifiable
        0x00,  # 0x44 : not user-modifiable
        0x00,  # 0x45 : not user-modifiable
        0x20,  # 0x46 : interrupt configuration 0->level low detection,
               # 1-> level high, 2-> Out of window, 3->In window, 0x20-> New sample ready , TBC
        0x0B,  # 0x47 : not user-modifiable
        0x00,  # 0x48 : not user-modifiable
        0x00,  # 0x49 : not user-modifiable
        0x02,  # 0x4a : not user-modifiable
        0x0A,  # 0x4b : not user-modifiable
        0x21,  # 0x4c : not user-modifiable
        0x00,  # 0x4d : not user-modifiable
        0x00,  # 0x4e : not user-modifiable
        0x05,  # 0x4f : not user-modifiable
        0x00,  # 0x50 : not user-modifiable
        0x00,  # 0x51 : not user-modifiable
        0x00,  # 0x52 : not user-modifiable
        0x00,  # 0x53 : not user-modifiable
        0xC8,  # 0x54 : not user-modifiable
        0x00,  # 0x55 : not user-modifiable
        0x00,  # 0x56 : not user-modifiable
        0x38,  # 0x57 : not user-modifiable
        0xFF,  # 0x58 : not user-modifiable
        0x01,  # 0x59 : not user-modifiable
        0x00,  # 0x5a : not user-modifiable
        0x08,  # 0x5b : not user-modifiable
        0x00,  # 0x5c : not user-modifiable
        0x00,  # 0x5d : not user-modifiable
        0x01,  # 0x5e : not user-modifiable
        0xDB,  # 0x5f : not user-modifiable
        0x0F,  # 0x60 : not user-modifiable
        0x01,  # 0x61 : not user-modifiable
        0xF1,  # 0x62 : not user-modifiable
        0x0D,  # 0x63 : not user-modifiable
        0x01,  # 0x64 : Sigma threshold MSB (mm in 14.2 format for MSB+LSB),
               # use SetSigmaThreshold(), default value 90 mm
        0x68,  # 0x65 : Sigma threshold LSB
        0x00,  # 0x66 : Min count Rate MSB (MCPS in 9.7 format for MSB+LSB), use SetSignalThreshold()
        0x80,  # 0x67 : Min count Rate LSB
        0x08,  # 0x68 : not user-modifiable
        0xB8,  # 0x69 : not user-modifiable
        0x00,  # 0x6a : not user-modifiable
        0x00,  # 0x6b : not user-modifiable
        0x00,  # 0x6c : Intermeasurement period MSB, 32 bits register, use SetIntermeasurementInMs()
        0x00,  # 0x6d : Intermeasurement period
        0x0F,  # 0x6e : Intermeasurement period
        0x89,  # 0x6f : Intermeasurement period LSB
        0x00,  # 0x70 : not user-modifiable
        0x00,  # 0x71 : not user-modifiable
        0x00,  # 0x72 : distance threshold high MSB (in mm, MSB+LSB), use SetD:tanceThreshold()
        0x00,  # 0x73 : distance threshold high LSB
        0x00,  # 0x74 : distance threshold low MSB ( in mm, MSB+LSB), use SetD:tanceThreshold()
        0x00,  # 0x75 : distance threshold low LSB
        0x00,  # 0x76 : not user-modifiable
        0x01,  # 0x77 : not user-modifiable
        0x0F,  # 0x78 : not user-modifiable
        0x0D,  # 0x79 : not user-modifiable
        0x0E,  # 0x7a : not user-modifiable
        0x0E,  # 0x7b : not user-modifiable
        0x00,  # 0x7c : not user-modifiable
        0x00,  # 0x7d : not user-modifiable
        0x02,  # 0x7e : not user-modifiable
        0xC7,  # 0x7f : ROI center, use SetROI()
        0xFF,  # 0x80 : XY ROI (X=Width, Y=Height), use SetROI()
        0x9B,  # 0x81 : not user-modifiable
        0x00,  # 0x82 : not user-modifiable
        0x00,  # 0x83 : not user-modifiable
        0x00,  # 0x84 : not user-modifiable
        0x01,  # 0x85 : not user-modifiable
        0x01,  # 0x86 : clear interrupt, use ClearInterrupt()
        0x40,  # 0x87 : start ranging, use StartRanging() or StopRanging(), If you want
               # an automatic start after VL53L1X_init() call, put 0x40 in location 0x87
    ]
)


class VL53L1X:
    def __init__(self, i2c, address=0x29):
        self.i2c = i2c
        self.address = address
        self.reset()
        time.sleep_ms(1)
        if self.read_model_id() != 0xEACC:
            raise RuntimeError("Failed to find expected ID register values. Check wiring!")
        # write default configuration
        self.i2c.writeto_mem(self.address, 0x2D, VL51L1X_DEFAULT_CONFIGURATION, addrsize=16)
        # the API triggers this change in VL53L1_init_and_start_range() once a
        # measurement is started; assumes MM1 and MM2 are disabled
        self.writeReg16Bit(0x001E, self.readReg16Bit(0x0022) * 4)
        time.sleep_ms(200)

    def writeReg(self, reg, value):
        return self.i2c.writeto_mem(self.address, reg, bytes([value]), addrsize=16)

    def writeReg16Bit(self, reg, value):
        return self.i2c.writeto_mem(
            self.address, reg, bytes([(value >> 8) & 0xFF, value & 0xFF]), addrsize=16
        )

    def readReg(self, reg):
        return self.i2c.readfrom_mem(self.address, reg, 1, addrsize=16)[0]

    def readReg16Bit(self, reg):
        data = self.i2c.readfrom_mem(self.address, reg, 2, addrsize=16)
        return (data[0] << 8) + data[1]

    def read_model_id(self):
        return self.readReg16Bit(0x010F)

    def reset(self):
        self.writeReg(0x0000, 0x00)
        time.sleep_ms(100)
        self.writeReg(0x0000, 0x01)

    # -- ROI (angle / field of view) -------------------------------------
    # ROI_CONFIG__USER_ROI_CENTRE_SPAD
    ROI_CENTER_REG = 0x007F
    # ROI_CONFIG__USER_ROI_REQUESTED_GLOBAL_XY_SIZE
    ROI_SIZE_REG = 0x0080

    def set_roi_center(self, center):
        """Move the measurement window to a different SPAD (changes the
        effective look direction). Valid centre SPADs are documented in the
        datasheet; 199 is the optical centre of the full array."""
        self.writeReg(self.ROI_CENTER_REG, center & 0xFF)

    # SPAD location map (from ST UM2555), looking into the front of the
    # sensor. col/row are 0-15, (0,0) = top-left of this table.
    # 199 (col=8, row=7) is the default/optical center.
    #
    # 128,136,144,152,160,168,176,184,  192,200,208,216,224,232,240,248
    # ...
    # 120,112,104, 96, 88, 80, 72, 64,   56, 48, 40, 32, 24, 16,  8,  0 <- Pin1
    #
    # IMPORTANT: the lens inverts the image (like a camera), so to shift the
    # real-world field of view, pick the SPAD on the *opposite* side of the
    # array from the direction you want to look.
    @staticmethod
    def spad_for_grid(col, row):
        """Return the SPAD number at raw array position col,row (0-15 each),
        using the orientation pictured above (not yet corrected for the
        lens inversion)."""
        col = max(0, min(15, col))
        row = max(0, min(15, row))
        if col < 8:
            base = 128 + col * 8
            return base + row if row < 8 else 127 - col * 8 - (row - 8)
        else:
            lc = col - 8
            base = 192 + lc * 8
            return base + row if row < 8 else 63 - lc * 8 - (row - 8)

    @classmethod
    def spad_for_direction(cls, right=0, up=0):
        """Convenience helper: pick a centre SPAD to shift the *real-world*
        field of view. right/up are roughly in SPAD-sized steps (about
        -7..+7); positive right looks further right, positive up looks
        further up. Handles the lens inversion internally."""
        col = 8 - right  # lens-inverted: real "right" -> array column decreases
        row = 7 + up      # lens-inverted: real "up" -> array row increases
        return cls.spad_for_grid(col, row)

    def set_roi(self, width, height):
        """Narrow (or widen) the field of view. width/height are given in
        SPADs, 4-16 each (16x16 = full ~27 deg FoV, 4x4 = narrowest ~ a few
        degrees). Mirrors ST's VL53L1X_SetROI()."""
        width = max(4, min(16, width))
        height = max(4, min(16, height))
        if width > 10 or height > 10:
            # outside the "small ROI" range: force the optical centre
            self.writeReg(self.ROI_CENTER_REG, 199)
        self.writeReg(self.ROI_SIZE_REG, ((height - 1) << 4) | (width - 1))

    # -- Distance mode (range) ---------------------------------------------
    # RANGE_CONFIG__VCSEL_PERIOD_A/B, RANGE_CONFIG__VALID_PHASE_HIGH,
    # SD_CONFIG__WOI_SD0, SD_CONFIG__INITIAL_PHASE_SD0
    DISTANCE_MODE_SHORT = 1  # ~1.3 m max, best ambient-light immunity
    DISTANCE_MODE_LONG = 2   # ~4 m max (default), more sensitive to ambient light

    def set_distance_mode(self, mode):
        """Switch between short-range (1) and long-range (2, default) timing
        configuration. Mirrors ST's VL53L1X_SetDistanceMode()."""
        if mode == self.DISTANCE_MODE_SHORT:
            self.writeReg(0x0060, 0x07)
            self.writeReg(0x0063, 0x05)
            self.writeReg(0x0069, 0x38)
            self.writeReg16Bit(0x0078, 0x0705)
            self.writeReg16Bit(0x007A, 0x0606)
        else:
            self.writeReg(0x0060, 0x0F)
            self.writeReg(0x0063, 0x0D)
            self.writeReg(0x0069, 0xB8)
            self.writeReg16Bit(0x0078, 0x0F0D)
            self.writeReg16Bit(0x007A, 0x0E0E)

    # -- Data-ready polling --------------------------------------------------
    # GPIO__TIO_HV_STATUS (bit0 toggles with each completed measurement,
    # compared against the fixed polarity baked into VL51L1X_DEFAULT_CONFIGURATION)
    INTR_STATUS_REG = 0x0031
    INTR_CLEAR_REG = 0x0086  # SYSTEM__INTERRUPT_CLEAR, write 0x01 to acknowledge

    def data_ready(self):
        """True once a new measurement has completed since the last
        clear_interrupt() call. Assumes the default active-high interrupt
        polarity from VL51L1X_DEFAULT_CONFIGURATION (never changed here)."""
        return (self.readReg(self.INTR_STATUS_REG) & 0x01) == 1

    def clear_interrupt(self):
        self.writeReg(self.INTR_CLEAR_REG, 0x01)

    def wait_for_data(self, timeout_ms=200, poll_ms=5):
        """Block until data_ready() or timeout_ms elapses (whichever first).
        Returns True if data became ready, False on timeout (caller may still
        read(), just risking slightly stale data)."""
        waited = 0
        while not self.data_ready():
            if waited >= timeout_ms:
                return False
            time.sleep_ms(poll_ms)
            waited += poll_ms
        return True

    def read(self):
        data = self.i2c.readfrom_mem(self.address, 0x0089, 17, addrsize=16)  # RESULT__RANGE_STATUS
        # range_status = data[0]
        # report_status = data[1]
        # stream_count = data[2]
        # dss_actual_effective_spads_sd0 = (data[3] << 8) + data[4]
        # peak_signal_count_rate_mcps_sd0 = (data[5]<<8) + data[6]
        # ambient_count_rate_mcps_sd0 = (data[7] << 8) + data[8]
        # sigma_sd0 = (data[9]<<8) + data[10]
        # phase_sd0 = (data[11]<<8) + data[12]
        final_crosstalk_corrected_range_mm_sd0 = (data[13] << 8) + data[14]
        # peak_signal_count_rate_crosstalk_corrected_mcps_sd0 = (data[15] << 8) + data[16]
        # status = None
        # if range_status in (17, 2, 1, 3):
        # status = "HardwareFail"
        # elif range_status == 13:
        # status = "MinRangeFail"
        # elif range_status == 18:
        # status = "SynchronizationInt"
        # elif range_status == 5:
        # status = "OutOfBoundsFail"
        # elif range_status == 4:
        # status = "SignalFail"
        # elif range_status == 6:
        # status = "SignalFail"
        # elif range_status == 7:
        # status = "WrapTargetFail"
        # elif range_status == 12:
        # status = "XtalkSignalFail"
        # elif range_status == 8:
        # status = "RangeValidMinRangeClipped"
        # elif range_status == 9:
        # if stream_count == 0:
        # status = "RangeValidNoWrapCheckFail"
        # else:
        # status = "OK"
        return final_crosstalk_corrected_range_mm_sd0
