# Entry point: hardware init, then
#   core1 (_thread): control_loop  IMU -> traction control -> PWM
#   core0 (main)   : udp_loop      UDP commands / poll reply / OLED
# See docs/system-architecture.md, docs/protocol.md
import _thread
import time
import ntptime
from utime import sleep
from Devices import Devices
import shared
import control_loop
import udp_loop


def str_date_time(datetime):
    return f"{datetime[0]:04}-{datetime[1]:02}-{datetime[2]:02} {datetime[3]:02}:{datetime[4]:02}:{datetime[5]:02}"


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


def main():
    dev = Devices().init()
    if dev.led0 is None or dev.wlan is None:
        raise RuntimeError("Devices initialization did not complete")

    sync_time()
    now = time.localtime(time.time() + 9 * 3600)  # JST adjustment
    print("Current time:", str_date_time(now))
    dev.oled.fill(0)
    dev.oled.text(f"Hello {now[1]:02}-{now[2]:02}!", 0, 0)
    dev.oled.show()

    shared.reset()
    # Wi-Fi (CYW43) stays on core0; the second thread runs on core1
    _thread.start_new_thread(control_loop.run, (dev,))
    try:
        udp_loop.run(dev)
    finally:
        shared.run[0] = 0
        udp_loop.wait_control_done()
        if not shared.stat[shared.STAT_DONE]:
            print("Warning: control loop did not stop in time")
        dev.led0.off()
        dev.wlan.disconnect()
        print("Finished.")


if __name__ == "__main__":
    main()
