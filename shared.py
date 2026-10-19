# State shared between core0 (udp_loop) and core1 (control_loop).
# Fixed-size arrays so neither loop allocates; each field has exactly one writer,
# so no lock is needed (single int writes are atomic).
from array import array
import time

# -- cmd: written by core0 (UDP), read by core1 (control) ---------------------
CMD_THROTTLE = 0    # 0-255
CMD_STEER = 1       # 0-180, 90 = centre
CMD_BRAKE = 2       # 0-255
CMD_STEER_OFS = 3   # -20..20 deg
CMD_ACCEL_RESP = 4  # 1-10
CMD_TC_LEVEL = 5    # 1-10
CMD_ESTOP = 6       # 0/1, latched until reset
CMD_LAST_RX_MS = 7  # time.ticks_ms() of the last valid packet
CMD_SIZE = 8

# -- stat: written by core1 (control), read by core0 (UDP / display) ----------
STAT_THR_US = 0
STAT_STEER_US = 1
STAT_AX = 2         # mg
STAT_AY = 3
STAT_AZ = 4
STAT_GZ = 5         # 0.1 dps
STAT_LOOP_US = 6
STAT_FAILSAFE = 7   # 0/1
STAT_ROLL = 8       # 0.01 deg
STAT_PITCH = 9      # 0.01 deg
STAT_DONE = 10      # 1 once control_loop has set outputs neutral and exited
STAT_SIZE = 11

cmd = array('i', [0] * CMD_SIZE)
stat = array('i', [0] * STAT_SIZE)
run = array('b', [1])   # set to 0 to stop both loops


def reset():
    for i in range(CMD_SIZE):
        cmd[i] = 0
    cmd[CMD_STEER] = 90
    cmd[CMD_ACCEL_RESP] = 5
    cmd[CMD_TC_LEVEL] = 5
    # start in failsafe: LAST_RX_MS far enough in the past
    cmd[CMD_LAST_RX_MS] = time.ticks_add(time.ticks_ms(), -1000000)
    for i in range(STAT_SIZE):
        stat[i] = 0
    stat[STAT_FAILSAFE] = 1
    run[0] = 1
