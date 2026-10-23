# Network protocol (UDP Binary)

## 1st byte

- 1=Accel
- 2=Steering
- 3=Break
- 4=Poling
- 5=System Stop
- 6=System Reset
- 7=Emergency stop
- 8=Setting

## 2nd byte

- 1=Accel:
  throttle value: 0~256
- 2=Steering:
  servo: 0~180 (90 is center)
- 3=Break:
  break value: 0~256

- 4=Poling: None
- 5=System Stop: None
- 6=System Reset: None
- 7=Emergency stop: None

- 8=Setting
  1= Steering offset degrees
  2= Accel response
  3= Traction control level

## 3rd byte (8=Setting Only)

- 1= Steering offset degrees -20~20
- 2= Accel response 1~10
- 3= Traction control level 1~10

The 3rd byte is interpreted as a signed int8 (-128 to 127); out-of-range values are clamped.

## Implementation notes

- Receive port: `config.UDP_PORT` (default 5000)
- Accel / Break are 1 byte, so the actual range is **0~255** (256 cannot be sent)
- When Break > 0, Break takes priority over Accel
- Packets that are too short or have an unknown command are dropped (they are not treated as keep-alive either)
- **Failsafe**: if no valid packet arrives for `config.FAILSAFE_MS` (default 500 ms), the throttle goes to neutral and the steering to center. While not sending commands, keep sending Poling(4) as a keep-alive
- **Emergency stop(7)** is latched. Outputs stay neutral until System Reset(6)
- System Stop(5): stops the control loop and the UDP loop (outputs are neutral)
- System Reset(6): sets outputs to neutral, then calls `machine.reset()`

## Poling(4) response

A 24-byte reply is sent back to the source address (**big-endian**, i.e. network byte order; `struct` format `>BBBBBBHHhhhhHhh`). Commands consist of single-byte values only, so byte order does not affect them.

| offset | type | content |
|--------|------|---------|
| 0 | u8 | `0x84` (response to 4) |
| 1 | u8 | flags: bit0=failsafe, bit1=emergency stop |
| 2 | u8 | Accel command value 0~255 |
| 3 | u8 | Steering command value 0~180 |
| 4 | u8 | Break command value 0~255 |
| 5 | u8 | Traction control level |
| 6 | u16 | ESC output pulse (us) |
| 8 | u16 | Servo output pulse (us) |
| 10 | i16 | accel X (mg) |
| 12 | i16 | accel Y (mg) |
| 14 | i16 | accel Z (mg) |
| 16 | i16 | gyro Z (0.1 dps) |
| 18 | u16 | Control loop period (us); about 4167 at 240 Hz |
| 20 | i16 | roll (0.01°). Complementary filter of accelerometer and gyro |
| 22 | i16 | pitch (0.01°) |

Accel and gyro values are converted from the sensor mounting orientation to the vehicle frame (X=forward, Y=left, Z=up; the upward axis is + for accel) via `config.IMU_AXIS_MAP`. Leaning right (right side down) raises the left side, so ay > 0 and roll > 0. Nose down gives ax < 0 and pitch > 0. To swap the roll and pitch values, use `config.ATTITUDE_SWAP_ROLL_PITCH` (default True).

roll = `atan2(ay, az)` and pitch = `atan2(-ax, sqrt(ay²+az²))` are used as the reference. Confirm the signs on the real vehicle (if reversed, flip them with `config.ATTITUDE_ROLL_SIGN` / `ATTITUDE_PITCH_SIGN`). Yaw is not reported because there is no magnetometer and it would drift.
