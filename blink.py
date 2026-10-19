from machine import ADC, Pin
from Devices import Devices
from utime import sleep
import time
import ntptime
import random
# import gc

def str_date_time(datetime):
    return f"{datetime[0]:04}-{datetime[1]:02}-{datetime[2]:02} {datetime[3]:02}:{datetime[4]:02}:{datetime[5]:02}"

def show_face(oled):
    faces = [
        [" (+_+) " ,"\\(^_^)/"       , " (^_^)/"      , " (>_<) " , " (;_;) " ,  " (0_0) " , " (@_@) "],
        [" /(`)\\ ", " `(`)'  ~*~ "  , " /(')'   u"   , " /(`)\\ ", " |(')| ",  " /(')\\ " , " /(`)\\ "],
        ["  / | " ,  "  / \\   \\|/" , "  | |   \\|/" , "  / | " ,  "  | | ",   "  / \\ "  , "  | \\ ~."]
        ]
    num = random.randint(0, len(faces[0]) - 1)
    for i, row in enumerate(faces):
        oled.text(row[num], 0, 32 + i * 10)


def sync_time(retries=3):
    for host in ("ntp.nict.jp", "pool.ntp.org", "time.google.com"):
        ntptime.host = host
        for _ in range(retries):
            try:
                ntptime.settime()
                return True
            except OSError as e:
                print("NTP failed:", host, e)
                sleep(1)
    return False

VSYS_STOP        = 3.6    # stop if VSYS stays below this voltage
VSYS_STOP_COUNT  = 3      # consecutive readings before stopping
VSYS_INTERVAL    = 8000   # measurement interval (msec seconds) 8 seconds
DISPLAY_INTERVAL = 1000   # display interval (msec seconds) 0.5 second


def get_slp(wait_usec=1000, timeout_usec=2000):
    before_usec = time.ticks_us()
    ecnt = 0
    def slp():
        nonlocal wait_usec
        nonlocal before_usec
        nonlocal ecnt
        now = time.ticks_us()
        interval = time.ticks_diff(now, before_usec)
        before_usec = now

        if interval == wait_usec:
            ecnt = 0
        elif interval < wait_usec:
            time.sleep_us(wait_usec - interval)
            ecnt = 0
        else:
            ecnt = ecnt + 1
            if ecnt > 1:
                # if ecnt > 4:
                now = time.localtime(time.time() + 9 * 3600)  # JST adjustment
                print(f"## Too Late:{ecnt} times: {now[3]:02}:{now[4]:02}:{now[5]:02} {interval} micro seconds!")
                ecnt = 0
                time.sleep_us(ecnt * 100 * wait_usec)
                before_usec = time.ticks_us()
        return interval
    return slp

def main():
    print("LED starts flashing...")

    dev = Devices().init()
    if dev.led0 is None or dev.wlan is None:
        raise RuntimeError("Devices initialization did not complete")

    sync_time()
    # dev.wlan.disconnect()
    now = time.localtime(time.time() + 9 * 3600)  # JST adjustment

    print("Current time:", str_date_time(now))
    print(f"Updating OLED({dev.oled}) display with current time...")
    dev.oled.fill(0)
    dev.oled.text(f"Hello {now[1]:02}-{now[2]:02}!", 0, 0)
    dev.oled.show()
    
    voltvsys = 0.0
    systemp = 0.0
    low = 0
    min = 0
    before_usec = time.ticks_us()
    disp_msec = None
    vsys_msec = None
    # gc.enable()
    # gc.collect()
    # gc.disable()
    interval = 0

    sleep = get_slp(4700,4700)
    while True:
        interval = sleep()
        usec = time.ticks_us()
        msec = time.ticks_ms()
        try:
            if vsys_msec is None or time.ticks_diff(msec, vsys_msec) >= VSYS_INTERVAL:
                vsys_msec = msec
                voltvsys = dev.read_vsys()
                systemp = dev.read_system_temp()
                print(f"VSYS: {voltvsys:.2f}V  {systemp:.2f}C wifi={dev.wlan.isconnected()}")
                low = low + 1 if voltvsys < VSYS_STOP else 0
                if low >= VSYS_STOP_COUNT:
                    dev.oled.fill(0)
                    dev.oled.text("LOW POWER", 0, 0)
                    dev.oled.text(f"VSYS:{voltvsys:.2f}V", 0, 10)
                    dev.oled.show()
                    print("Low power, stopping.")
                    break
        
            # distance = dev.read_distance()
            distance = None
            # direction = dev.scan_directions() # measure distance
            # print(f"Time before scanning directions: {befor}: {time.time()}")
            # for grid_row in dev.scan_grid():
            #     print("Grid:", grid_row)
            # if distance is not None and distance < 1000:
            #     print("Something is very close!")
            imu = dev.read_imu()

            if disp_msec is None or time.ticks_diff(msec, disp_msec) >= DISPLAY_INTERVAL:
                disp_msec = msec
                dev.led0.toggle()
                now = time.localtime(time.time() + 9 * 3600)  # JST adjustment
                if imu is None:
                    print("IMU: unavailable")
                else:
                    ax, ay, az = imu["accel"]
                    gx, gy, gz = imu["gyro"]
                    print(
                        f"{interval}us Dist: {distance}mm/ IMU a(g): {ax:.3f} {ay:.3f} {az:.3f}  g(dps): {gx:.1f} {gy:.1f} {gz:.1f}  t:{imu['temp']:.1f}C".format(
                            ax, ay, az, gx, gy, gz, imu["temp"]
                        )
                    )
                dist_str = f"{distance}" if distance is not None else "N/A"
                dev.oled.fill(0)
                dev.oled.text(f"{now[1]:02}-{now[2]:02} {now[3]:02}:{now[4]:02}:{now[5]:02}", 0, 0)
                dev.oled.text(f"{voltvsys:.2f}v {systemp:.2f} C", 0, 10)
                dev.oled.text(f"Dist: {dist_str}mm", 0, 20)
                show_face(dev.oled)
                dev.oled.show()
        except Exception as e:
            print("Exception:", type(e).__name__, repr(e))

        except KeyboardInterrupt:
            break
        
        # if time.ticks_diff(usec, before_usec) >= 2000:
        #     now = time.localtime(time.time() + 9 * 3600)  # JST adjustment
        #     print(f"## Too Late: {now[1]:02}-{now[2]:02} {now[3]:02}:{now[4]:02}:{now[5]:02} {time.ticks_diff(usec, before_usec)} micro seconds!")
        
        before_usec = usec

    # gc.enable()
    # gc.collect()
    dev.led0.off()
    dev.wlan.disconnect()
    print("Finished.")


if __name__ == "__main__":
    main()
    