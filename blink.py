from machine import ADC, Pin
from Devices import Devices
from utime import sleep
import time
import ntptime
import random

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
        # print(row[num])
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

VSYS_STOP = 3.6      # この電圧未満が続いたら停止
VSYS_STOP_COUNT = 3  # 連続回数
VSYS_INTERVAL = 8    # 測定間隔(秒)

def main():
    print("LED starts flashing...")

    dev = Devices().init()
    if dev.led0 is None or dev.wlan is None:
        raise RuntimeError("Devices initialization did not complete")

    sync_time()
    now = time.localtime(time.time() + 9 * 3600)  # JST adjustment

    print("Current time:", str_date_time(now))
    print(f"Updating OLED({dev.oled}) display with current time...")
    dev.oled.fill(0)
    dev.oled.text("Current time:", 0, 0)
    dev.oled.show()
    
    voltvsys = 0.0
    systemp = 0.0
    low = 0
    tick = 0
    min = 0
    while True:
        try:
            if tick % VSYS_INTERVAL == 0:
                tick = 1
                voltvsys = dev.read_vsys()
                systemp = dev.read_system_temp()
                # print(f"VSYS: {voltvsys:.2f}V wifi={dev.wlan.isconnected()}")
                low = low + 1 if voltvsys < VSYS_STOP else 0
                if low >= VSYS_STOP_COUNT:
                    dev.oled.fill(0)
                    dev.oled.text("LOW POWER", 0, 0)
                    dev.oled.text(f"VSYS:{voltvsys:.2f}V", 0, 10)
                    dev.oled.show()
                    print("Low power, stopping.")
                    break
            
            now = time.localtime(time.time() + 9 * 3600)  # JST adjustment
            # if now[4] % 10 == 0:
            #     print("Syncing time...")
            #     sync_time()

            tick += 1
            dev.led0.toggle()
            distance = dev.read_distance()
            direction = dev.scan_directions() # measure distance
            # print(f"Time before scanning directions: {befor}: {time.time()}")
            print("Distance:", distance)
            print("Direction distance:", direction)
            # for grid_row in dev.scan_grid():
            #     print("Grid:", grid_row)
            dist_str = f"{distance}" if distance is not None else "N/A"
            # if distance is not None and distance < 1000:
            #     print("Something is very close!")
            print("time:", str_date_time(now), "dist:", dist_str)
            dev.oled.fill(0)
            dev.oled.text(f"{now[1]:02}-{now[2]:02} {now[3]:02}:{now[4]:02}:{now[5]:02}", 0, 0)
            dev.oled.text(f"{voltvsys:.2f}v {systemp:.2f} C", 0, 10)
            dev.oled.text(f"Dist: {dist_str}mm", 0, 20)
            show_face(dev.oled)
            dev.oled.show()
            sleep(1) # sleep 1s
        except KeyboardInterrupt:
            break
    dev.led0.off()
    dev.wlan.disconnect()
    print("Finished.")



if __name__ == "__main__":
    main()
    