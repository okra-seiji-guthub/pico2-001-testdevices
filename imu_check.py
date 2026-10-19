# One-shot LSM6DSV16X check. Does not start Wi-Fi, the OLED, or the distance sensor.
# After the 6A jumper is closed, a resting board should show about 1 g on one axis
# and gyro rates near 0 dps.

from machine import I2C, Pin
import time

import config
import lsm6dsv16x


def main():
    i2c = I2C(0, scl=Pin(config.I2C_SCL0), sda=Pin(config.I2C_SDA0), freq=400000)
    found = i2c.scan()
    print("I2C0 addresses:", [hex(addr) for addr in found])

    address = config.LSM6DSV16X_ADDR
    if address not in found:
        other = 0x6B if address == 0x6A else 0x6A
        if other not in found:
            raise RuntimeError("LSM6DSV16X address 0x{:02X} not on I2C0".format(address))
        print("using 0x{:02X}".format(other))
        address = other

    imu = lsm6dsv16x.LSM6DSV16X(
        i2c,
        address=address,
        accel_odr=config.LSM6DSV16X_ACCEL_ODR_HZ,
        gyro_odr=config.LSM6DSV16X_GYRO_ODR_HZ,
        accel_fs=config.LSM6DSV16X_ACCEL_FS_G,
        gyro_fs=config.LSM6DSV16X_GYRO_FS_DPS,
    )
    for _ in range(5):
        sample = imu.read()
        ax, ay, az = sample["accel"]
        gx, gy, gz = sample["gyro"]
        print(
            "a(g): {:.3f} {:.3f} {:.3f}  g(dps): {:.1f} {:.1f} {:.1f}  t:{:.1f}C".format(
                ax, ay, az, gx, gy, gz, sample["temp"]
            )
        )
        time.sleep_ms(200)


if __name__ == "__main__":
    main()
