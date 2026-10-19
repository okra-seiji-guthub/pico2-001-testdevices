"""Interactive prompt for the Pico UDP remote control (docs/protocol.md).

  uv run python tools/udp_shell.py <pico-ip>

  >> f100      accelerate: throttle 100 (0-255), releases the brake
  >> b100      brake 100 (0-255), releases the throttle
  >> l90       steer left 90 deg  (full left)
  >> r30       steer right 30 deg
  >> c         steering centre
  >> s         stop: throttle 0, brake 0, steering centre
  >> f100 l30  several commands on one line
  >> p         poll and show the car's state
  >> set steer-offset -5     (also: accel-response, tc-level)
  >> e         emergency stop (latched until the car is reset)
  >> stop | reset | h | q

The current command is resent at 20 Hz in the background, so the car's
500 ms failsafe does not trigger while this shell is open.
Quitting (q, Ctrl+C, Ctrl+D) sends throttle 0 / brake 0 / steering centre first.
"""
import argparse
import threading
import time

import udp_client as uc

try:
    import readline  # noqa: F401  (line editing / history where available)
except ImportError:
    pass

SEND_HZ = 20
CENTER = 90


class Car:
    """Current command state plus the background keep-alive sender."""

    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr
        self.throttle = 0
        self.brake = 0
        self.steer = CENTER
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self):
        self._thread.start()

    def _send(self, data):
        try:
            self.sock.sendto(data, self.addr)
        except OSError:
            pass  # e.g. ICMP unreachable on Windows; the poll will report it

    def _loop(self):
        period = 1.0 / SEND_HZ
        while not self._stop.is_set():
            self._send(bytes([2, self.steer]))
            self._send(bytes([3, self.brake]))
            self._send(bytes([1, self.throttle]))
            self._stop.wait(period)

    def neutral(self):
        self.throttle, self.brake, self.steer = 0, 0, CENTER

    def close(self):
        self.neutral()
        for _ in range(3):  # make sure it gets through, then stop the sender
            self._send(bytes([3, 0]))
            self._send(bytes([1, 0]))
            self._send(bytes([2, CENTER]))
            time.sleep(0.02)
        self._stop.set()
        self._thread.join(timeout=1)


def parse_value(tok, name, lo, hi):
    try:
        v = int(tok)
    except ValueError:
        raise ValueError(f"{name}: number expected, got {tok!r}")
    if not lo <= v <= hi:
        raise ValueError(f"{name} must be {lo}-{hi}")
    return v


def run_command(car, tokens, i):
    """Execute the command at tokens[i]; return the index of the next one."""
    tok = tokens[i].lower()
    c, arg = tok[0], tok[1:]

    if c == "f" and arg:
        car.throttle, car.brake = parse_value(arg, "throttle", 0, 255), 0
    elif c == "b" and arg:
        car.brake, car.throttle = parse_value(arg, "brake", 0, 255), 0
    elif c == "l" and arg:
        car.steer = CENTER - parse_value(arg, "left", 0, 90)
    elif c == "r" and arg:
        car.steer = CENTER + parse_value(arg, "right", 0, 90)
    elif tok == "c":
        car.steer = CENTER
    elif tok == "s":
        car.neutral()
    elif tok == "p":
        uc.show(uc.poll(car.sock, car.addr))
    elif tok in ("e", "estop"):
        car._send(bytes([7]))
        print("emergency stop sent (latched until the car is reset)")
    elif tok in ("stop", "reset"):
        car.neutral()
        car._send(bytes([{"stop": 5, "reset": 6}[tok]]))
        print(f"{tok} sent")
    elif tok == "set":
        if i + 2 >= len(tokens):
            raise ValueError(f"usage: set <{'|'.join(uc.SETTINGS)}> <value>")
        name = tokens[i + 1].lower()
        if name not in uc.SETTINGS:
            raise ValueError(f"unknown setting {name!r} ({', '.join(uc.SETTINGS)})")
        code, lo, hi = uc.SETTINGS[name]
        v = parse_value(tokens[i + 2], name, lo, hi)
        car._send(bytes([8, code, v & 0xFF]))
        return i + 3
    elif tok in ("h", "help", "?"):
        print(__doc__)
    else:
        raise ValueError(f"unknown command {tokens[i]!r} (h for help)")
    return i + 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("host")
    ap.add_argument("--port", type=int, default=uc.PORT)
    ap.add_argument("--timeout", type=float, default=0.3, help="poll reply timeout (s)")
    a = ap.parse_args()

    car = Car(uc.make_socket(a.timeout), (a.host, a.port))
    car.start()
    print(f"connected to {a.host}:{a.port}  (h = help, q = quit)")
    try:
        while True:
            try:
                line = input(">> ")
            except EOFError:
                break
            tokens = line.split("#", 1)[0].split()  # "# ..." is a comment
            if not tokens:
                continue
            if tokens[0].lower() in ("q", "quit", "exit"):
                break
            i = 0
            try:
                while i < len(tokens):
                    i = run_command(car, tokens, i)
            except ValueError as e:
                print("error:", e)
            else:
                print(f"thr={car.throttle} brk={car.brake} steer={car.steer - CENTER:+d} "
                      f"({'L' if car.steer < CENTER else 'R' if car.steer > CENTER else 'C'})")
    except KeyboardInterrupt:
        print()
    finally:
        car.close()
        print("neutral sent, bye")


if __name__ == "__main__":
    main()
