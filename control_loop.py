# core1: IMU -> traction control -> PWM out (ESC / servo).
# No Wi-Fi, OLED or print here; keep the loop jitter low.
# Integer math only, to avoid boxing floats on every iteration.
from machine import Pin, PWM
import time
import config
import shared as sh
from attitude import Attitude

IMU_PERIOD_US = 4167      # 240 Hz; used for pacing only when the IMU is missing

# accel response 1-10 -> max throttle change per loop (us). 10 -> ~0.1 s full scale, 1 -> ~1 s
SLEW_US_PER_RESP = 2

# traction control: horizontal G (|ax|+|ay|, mg) above the threshold cuts forward throttle.
# level 10 -> 500 mg (intervenes early), level 1 -> 1400 mg. Tune on the real car.
TC_BASE_MG = 1500
TC_STEP_MG = 100
TC_MIN_LIMIT_PCT = 30


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def _pwm(pin):
    p = PWM(Pin(pin))
    p.freq(config.PWM_FREQ_HZ)
    return p


def _tc_limit_pct(ax, ay, level):
    h = abs(ax) + abs(ay)
    thresh = TC_BASE_MG - level * TC_STEP_MG
    if h <= thresh:
        return 100
    return _clamp(100 - (h - thresh) * 100 // thresh, TC_MIN_LIMIT_PCT, 100)


def run(dev):
    cmd = sh.cmd
    stat = sh.stat
    neutral = config.ESC_NEUTRAL_US
    fwd_range = config.ESC_MAX_US - neutral
    brk_range = neutral - config.ESC_MIN_US
    s_center = config.SERVO_CENTER_US
    s_range = config.SERVO_RANGE_US

    esc = None
    servo = None
    try:
        esc = _pwm(config.ESC_PIN)
        servo = _pwm(config.SERVO_PIN)
        esc.duty_ns(neutral * 1000)
        servo.duty_ns(s_center * 1000)

        imu = dev.imu
        (mx, sx), (my, sy), (mz, sz) = config.IMU_AXIS_MAP
        swap_rp = config.ATTITUDE_SWAP_ROLL_PITCH
        att =Attitude(config.ATTITUDE_ALPHA, config.ATTITUDE_ROLL_SIGN, config.ATTITUDE_PITCH_SIGN)
        thr_us = neutral
        prev = time.ticks_us()
        while sh.run[0]:
            # 1. IMU (blocks until a new 240 Hz sample)
            if imu is not None:
                try:
                    s = imu.read()
                    sa = s["accel"]
                    sg = s["gyro"]
                    # sensor frame -> car frame (config.IMU_AXIS_MAP)
                    ax, ay, az = sa[mx] * sx, sa[my] * sy, sa[mz] * sz
                    gx, gy, gz = sg[mx] * sx, sg[my] * sy, sg[mz] * sz
                    stat[sh.STAT_AX] = int(ax * 1000)
                    stat[sh.STAT_AY] = int(ay * 1000)
                    stat[sh.STAT_AZ] = int(az * 1000)
                    stat[sh.STAT_GZ] = int(gz * 10)
                    att.update(ax, ay, az, gx, gy, stat[sh.STAT_LOOP_US] * 1e-6)
                    if swap_rp:
                        stat[sh.STAT_ROLL] = int(att.pitch * 100)
                        stat[sh.STAT_PITCH] = int(att.roll * 100)
                    else:
                        stat[sh.STAT_ROLL] = int(att.roll * 100)
                        stat[sh.STAT_PITCH] = int(att.pitch * 100)
                except Exception:
                    pass  # keep previous values
            else:
                wait = IMU_PERIOD_US - time.ticks_diff(time.ticks_us(), prev)
                if wait > 0:
                    time.sleep_us(wait)

            now_us = time.ticks_us()
            stat[sh.STAT_LOOP_US] = time.ticks_diff(now_us, prev)
            prev = now_us

            # 2. failsafe
            failsafe = cmd[sh.CMD_ESTOP] or \
                time.ticks_diff(time.ticks_ms(), cmd[sh.CMD_LAST_RX_MS]) > config.FAILSAFE_MS

            # 3-5. throttle
            if failsafe:
                thr_us = neutral
                steer = 90
            else:
                brake = cmd[sh.CMD_BRAKE]
                steer = cmd[sh.CMD_STEER] + cmd[sh.CMD_STEER_OFS]
                if brake > 0:
                    thr_us = neutral - brake * brk_range // 255   # brake applies at once
                else:
                    limit = _tc_limit_pct(stat[sh.STAT_AX], stat[sh.STAT_AY], cmd[sh.CMD_TC_LEVEL])
                    target = neutral + cmd[sh.CMD_THROTTLE] * fwd_range * limit // (255 * 100)
                    if target > thr_us:
                        step = cmd[sh.CMD_ACCEL_RESP] * SLEW_US_PER_RESP
                        thr_us = target if target - thr_us <= step else thr_us + step
                    else:
                        thr_us = target   # easing off / TC cut applies at once

            # 6. steering
            steer_us = _clamp(s_center + (steer - 90) * s_range // 90,
                              s_center - s_range, s_center + s_range)

            # 7. output
            esc.duty_ns(thr_us * 1000)
            servo.duty_ns(steer_us * 1000)
            stat[sh.STAT_THR_US] = thr_us
            stat[sh.STAT_STEER_US] = steer_us
            stat[sh.STAT_FAILSAFE] = 1 if failsafe else 0
    except Exception:
        pass
    finally:
        try:
            if esc is not None:
                esc.duty_ns(neutral * 1000)
            if servo is not None:
                servo.duty_ns(s_center * 1000)
        except Exception:
            pass
        stat[sh.STAT_THR_US] = neutral
        stat[sh.STAT_STEER_US] = s_center
        sh.run[0] = 0
        stat[sh.STAT_DONE] = 1
