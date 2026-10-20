# core0: UDP command receive (non-blocking), poll reply, low-rate OLED / VSYS / LED.
# Packet format: docs/protocol.md
import machine
import socket
import struct
import time
import config
import shared as sh

CMD_ACCEL = 1
CMD_STEERING = 2
CMD_BRAKE = 3
CMD_POLL = 4
CMD_STOP = 5
CMD_RESET = 6
CMD_ESTOP = 7
CMD_SETTING = 8

SET_STEER_OFS = 1
SET_ACCEL_RESP = 2
SET_TC_LEVEL = 3

POLL_REPLY = 0x84
POLL_FMT = ">BBBBBBHHhhhhHhh"  # big-endian (network byte order)

VSYS_STOP = 3.6       # stop if VSYS stays below this voltage
VSYS_STOP_COUNT = 3   # consecutive readings before stopping


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def _s8(b):
    return b - 256 if b > 127 else b


def _poll_reply():
    cmd = sh.cmd
    stat = sh.stat
    flags = (stat[sh.STAT_FAILSAFE] & 1) | ((cmd[sh.CMD_ESTOP] & 1) << 1)
    return struct.pack(
        POLL_FMT, POLL_REPLY, flags,
        cmd[sh.CMD_THROTTLE], cmd[sh.CMD_STEER], cmd[sh.CMD_BRAKE], cmd[sh.CMD_TC_LEVEL],
        stat[sh.STAT_THR_US], stat[sh.STAT_STEER_US],
        stat[sh.STAT_AX], stat[sh.STAT_AY], stat[sh.STAT_AZ], stat[sh.STAT_GZ],
        _clamp(stat[sh.STAT_LOOP_US], 0, 0xFFFF),
        _clamp(stat[sh.STAT_ROLL], -32768, 32767), _clamp(stat[sh.STAT_PITCH], -32768, 32767),
    )


def wait_control_done(timeout_ms=200):
    t0 = time.ticks_ms()
    while not sh.stat[sh.STAT_DONE] and time.ticks_diff(time.ticks_ms(), t0) < timeout_ms:
        time.sleep_ms(5)


def handle(sock, pkt, addr):
    """Apply one packet. Returns False if it was malformed (and ignored)."""
    cmd = sh.cmd
    n = len(pkt)
    if n < 1:
        return False
    c = pkt[0]
    if c in (CMD_ACCEL, CMD_STEERING, CMD_BRAKE):
        if n < 2:
            return False
        if c == CMD_ACCEL:
            cmd[sh.CMD_THROTTLE] = pkt[1]
        elif c == CMD_STEERING:
            cmd[sh.CMD_STEER] = min(pkt[1], 180)
        else:
            cmd[sh.CMD_BRAKE] = pkt[1]
    elif c == CMD_POLL:
        sock.sendto(_poll_reply(), addr)
    elif c == CMD_STOP:
        print("UDP: system stop")
        sh.run[0] = 0
    elif c == CMD_RESET:
        print("UDP: system reset")
        sh.run[0] = 0
        wait_control_done()
        machine.reset()
    elif c == CMD_ESTOP:
        cmd[sh.CMD_ESTOP] = 1
    elif c == CMD_SETTING:
        if n < 3:
            return False
        kind = pkt[1]
        v = _s8(pkt[2])
        if kind == SET_STEER_OFS:
            cmd[sh.CMD_STEER_OFS] = _clamp(v, -20, 20)
        elif kind == SET_ACCEL_RESP:
            cmd[sh.CMD_ACCEL_RESP] = _clamp(v, 1, 10)
        elif kind == SET_TC_LEVEL:
            cmd[sh.CMD_TC_LEVEL] = _clamp(v, 1, 10)
        else:
            return False
    else:
        return False
    cmd[sh.CMD_LAST_RX_MS] = time.ticks_ms()
    return True


def show_status(dev, ip, voltvsys, systemp):
    cmd = sh.cmd
    stat = sh.stat
    state = "ESTOP" if cmd[sh.CMD_ESTOP] else "FAILSAFE" if stat[sh.STAT_FAILSAFE] else "RUN"
    print(f"{state} thr={stat[sh.STAT_THR_US]}us str={stat[sh.STAT_STEER_US]}us "
          f"loop={stat[sh.STAT_LOOP_US]}us a(mg)={stat[sh.STAT_AX]} {stat[sh.STAT_AY]} {stat[sh.STAT_AZ]} "
          f"roll={stat[sh.STAT_ROLL] / 100:.1f} pitch={stat[sh.STAT_PITCH] / 100:.1f} "
          f"VSYS={voltvsys:.2f}V {systemp:.1f}C")
    dev.oled.fill(0)
    dev.oled.text(f"{ip}", 0, 0)
    dev.oled.text(f"UDP:{config.UDP_PORT}", 0, 10)
    dev.oled.text(state, 0, 20)
    dev.oled.text(f"T{stat[sh.STAT_THR_US]} S{stat[sh.STAT_STEER_US]}", 0, 30)
    dev.oled.text(f"R{stat[sh.STAT_ROLL] / 100:+.1f} P{stat[sh.STAT_PITCH] / 100:+.1f}", 0, 40)
    dev.oled.text(f"{voltvsys:.2f}v {systemp:.1f}C", 0, 50)
    dev.oled.show()


def run(dev):
    ip = dev.wlan.ifconfig()[0]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", config.UDP_PORT))
    sock.setblocking(False)
    print(f"UDP listening on {ip}:{config.UDP_PORT}")

    status_ms = None
    low = 0
    try:
        while sh.run[0]:
            # drain every pending packet
            while True:
                try:
                    pkt, addr = sock.recvfrom(8)
                except OSError:
                    break  # EAGAIN: nothing pending
                try:
                    handle(sock, pkt, addr)
                except OSError as e:
                    print("UDP send failed:", e)

            msec = time.ticks_ms()
            if status_ms is None or time.ticks_diff(msec, status_ms) >= config.STATUS_INTERVAL_MS:
                status_ms = msec
                try:
                    voltvsys = dev.read_vsys()
                    systemp = dev.read_system_temp()
                    low = low + 1 if voltvsys < VSYS_STOP else 0
                    if low >= VSYS_STOP_COUNT:
                        dev.oled.fill(0)
                        dev.oled.text("LOW POWER", 0, 0)
                        dev.oled.text(f"VSYS:{voltvsys:.2f}V", 0, 10)
                        dev.oled.show()
                        print("Low power, stopping.")
                        sh.run[0] = 0
                        break
                    dev.led0.toggle()
                    show_status(dev, ip, voltvsys, systemp)
                except Exception as e:
                    print("Status exception:", type(e).__name__, repr(e))

            time.sleep_ms(1)
    finally:
        sock.close()
