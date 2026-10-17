# Sample configuration for Wokwi
# Real hardware configuration and Wi-Fi password should be written in config_local.py (not managed by git).

WIFI_SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""

I2C_SDA0 = 8
I2C_SCL0 = 9
I2C_SDA1 = 10
I2C_SCL1 = 11


OLED_ADDR = 0x3C   # SA0 = GND
OLED_CONTRAST = 0x01  # 0x00 (dim) to 0xFF (maximum brightness, default)
OLED_PRECHARGE = 0x11  # Precharge period; values below the default 0xF1 (internal) dim the display
OLED_VCOM_DESEL = 0x11  # VCOM deselect voltage; values below the default 0x30 dim the display
BME_ADDR  = 0x76   # SDO = GND
VL53L1X_ADDR = 0x29  # default VL53L1X I2C address
LSM6DSV16X_ADDR = 0x6B  # this board answers at 0x6B with both address jumpers open; close 6A to select 0x6A
LSM6DSV16X_ACCEL_ODR_HZ = 120
LSM6DSV16X_GYRO_ODR_HZ = 120
LSM6DSV16X_ACCEL_FS_G = 4
LSM6DSV16X_GYRO_FS_DPS = 2000
VL53L1X_ROI_WIDTH = 16   # 4-16 SPADs; smaller = narrower field of view (angle)
VL53L1X_ROI_HEIGHT = 16  # 4-16 SPADs; 16x16 = full ~27 deg FoV, 4x4 = narrowest
VL53L1X_DISTANCE_MODE = 2  # 1 = Short (~1.3m, less ambient-light sensitive), 2 = Long (~4m, default)
VL53L1X_REVERSE = False  # False = current mounting; True = sensor rotated 180 deg (upside-down),
                          # flips left/right and up/down of scan_directions() / scan_grid()

# -- left/front/right directional scan (scan_directions()) -----------------
VL53L1X_SCAN_ROI_SIZE = 8     # 4-10 SPADs; narrow ROI used while scanning each direction
VL53L1X_SCAN_SPAD_OFFSET = 4  # SPAD-steps to shift left/right (roughly 1 step ~ 1.7 deg)
VL53L1X_SCAN_SETTLE_MS = 100  # max wait per direction for a fresh measurement (data-ready polling
                               # returns earlier if the sensor finishes sooner); also used as the
                               # worst-case fallback delay if data-ready polling times out

# -- grid scan (scan_grid()) -------------------------------------------------
VL53L1X_GRID_COLS = 3        # horizontal cells
VL53L1X_GRID_ROWS = 3        # vertical cells
VL53L1X_GRID_ROI_SIZE = 5    # 4-10 SPADs; per-cell ROI (smaller = narrower, less signal)
VL53L1X_GRID_STEP = 4        # SPAD-steps between neighbouring cells
VL53L1X_GRID_SETTLE_MS = 60  # max wait per cell (data-ready polling returns earlier)

LED_EXT_PIN = 15
ADC_PIN = 29



# override with config_local.py if available
try:
    from config_local import *
except ImportError:
    pass
