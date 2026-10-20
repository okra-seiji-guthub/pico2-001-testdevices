"""PC-side test client for the Pico UDP remote control (docs/protocol.md).

Examples:
  uv run python tools/udp_client.py 192.168.1.50 poll
  uv run python tools/udp_client.py 192.168.1.50 monitor
  uv run python tools/udp_client.py 192.168.1.50 drive --throttle 128 --steer 90 --seconds 3
  uv run python tools/udp_client.py 192.168.1.50 steer 0
  uv run python tools/udp_client.py 192.168.1.50 set steer-offset -5
  uv run python tools/udp_client.py 192.168.1.50 estop

Note: the car goes to failsafe 500 ms after the last valid packet, so a single
"throttle" command only lasts that long. Use "drive" to hold a command.
"""
import argparse
import socket
import struct
import time

PORT = 5000
POLL_FMT = ">BBBBBBHHhhhhHhh"  # big-endian (network byte order)
POLL_SIZE = struct.calcsize(POLL_FMT)
SETTINGS = {"steer-offset": (1, -20, 20), "accel-response": (2, 1, 10), "tc-level": (3, 1, 10)}


def make_socket(timeout):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    return s


def poll(sock, addr):
    """Send Poling(4) and return the decoded reply, or None on timeout."""
    sock.sendto(bytes([4]), addr)
    try:
        data, _ = sock.recvfrom(64)
    except (socket.timeout, ConnectionResetError):  # Windows reports ICMP unreachable this way
        return None
    if len(data) != POLL_SIZE or data[0] != 0x84:
        print(f"unexpected reply: {data!r}")
        return None
    (_, flags, thr, steer, brk, tc, thr_us, steer_us, ax, ay, az, gz, loop_us, roll, pitch) = struct.unpack(POLL_FMT, data)
    return {
        "failsafe": bool(flags & 1), "estop": bool(flags & 2),
        "cmd_throttle": thr, "cmd_steer": steer, "cmd_brake": brk, "tc_level": tc,
        "esc_us": thr_us, "servo_us": steer_us,
        "accel_mg": (ax, ay, az), "gyro_z_dps": gz / 10, "loop_us": loop_us,
        "roll_deg": roll / 100, "pitch_deg": pitch / 100,
    }


def show(r):
    if r is None:
        print("no reply (timeout)")
        return
    flags = [n for n in ("failsafe", "estop") if r[n]] or ["ok"]
    print(f"[{','.join(flags)}] cmd thr={r['cmd_throttle']} str={r['cmd_steer']} brk={r['cmd_brake']} "
          f"tc={r['tc_level']} | out esc={r['esc_us']}us servo={r['servo_us']}us | "
          f"a(mg)={r['accel_mg']} gz={r['gyro_z_dps']:.1f}dps roll={r['roll_deg']:+.1f} pitch={r['pitch_deg']:+.1f} "
          f"loop={r['loop_us']}us")


def drive(sock, addr, throttle, steer, brake, seconds, rate):
    """Hold a command for `seconds`, resending at `rate` Hz (keeps the failsafe away)."""
    period = 1.0 / rate
    end = time.monotonic() + seconds
    last_show = 0.0
    while time.monotonic() < end:
        t0 = time.monotonic()
        sock.sendto(bytes([2, steer]), addr)
        sock.sendto(bytes([3, brake]), addr)
        sock.sendto(bytes([1, throttle]), addr)
        if t0 - last_show >= 0.5:  # poll doubles as telemetry
            last_show = t0
            show(poll(sock, addr))
        time.sleep(max(0.0, period - (time.monotonic() - t0)))
    # release: neutral throttle, then centre
    sock.sendto(bytes([1, 0]), addr)
    sock.sendto(bytes([3, 0]), addr)
    sock.sendto(bytes([2, 90]), addr)
    print("released")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("host")
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--timeout", type=float, default=1.0)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("poll", help="send Poling once and print the reply")
    m = sub.add_parser("monitor", help="poll repeatedly (also acts as keep-alive)")
    m.add_argument("--hz", type=float, default=5)
    for name, hi in (("throttle", 255), ("steer", 180), ("brake", 255)):
        p = sub.add_parser(name, help=f"send one {name} packet (0-{hi})")
        p.add_argument("value", type=int)
    d = sub.add_parser("drive", help="hold throttle/steer/brake, resending at --rate Hz")
    d.add_argument("--throttle", type=int, default=0)
    d.add_argument("--steer", type=int, default=90)
    d.add_argument("--brake", type=int, default=0)
    d.add_argument("--seconds", type=float, default=3)
    d.add_argument("--rate", type=float, default=20)
    s = sub.add_parser("set", help="change a setting")
    s.add_argument("name", choices=SETTINGS)
    s.add_argument("value", type=int)
    for name in ("stop", "reset", "estop"):
        sub.add_parser(name, help=f"send {name}")

    a = ap.parse_args()
    addr = (a.host, a.port)
    sock = make_socket(a.timeout)

    if a.cmd == "poll":
        show(poll(sock, addr))
    elif a.cmd == "monitor":
        try:
            while True:
                show(poll(sock, addr))
                time.sleep(1.0 / a.hz)
        except KeyboardInterrupt:
            pass
    elif a.cmd in ("throttle", "steer", "brake"):
        code, hi = {"throttle": (1, 255), "steer": (2, 180), "brake": (3, 255)}[a.cmd]
        if not 0 <= a.value <= hi:
            ap.error(f"{a.cmd} must be 0-{hi}")
        sock.sendto(bytes([code, a.value]), addr)
    elif a.cmd == "drive":
        if not (0 <= a.throttle <= 255 and 0 <= a.steer <= 180 and 0 <= a.brake <= 255):
            ap.error("throttle/brake 0-255, steer 0-180")
        try:
            drive(sock, addr, a.throttle, a.steer, a.brake, a.seconds, a.rate)
        except KeyboardInterrupt:
            sock.sendto(bytes([1, 0]), addr)
            print("\ninterrupted: throttle 0 sent")
    elif a.cmd == "set":
        code, lo, hi = SETTINGS[a.name]
        if not lo <= a.value <= hi:
            ap.error(f"{a.name} must be {lo}..{hi}")
        sock.sendto(bytes([8, code, a.value & 0xFF]), addr)
    else:
        sock.sendto(bytes([{"stop": 5, "reset": 6, "estop": 7}[a.cmd]]), addr)


if __name__ == "__main__":
    main()
