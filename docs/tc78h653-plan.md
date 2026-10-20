# Plan: drive the motor with a TC78H653FTG (and add reverse)

Status: **plan only, not implemented.** Implementation goes on a separate feature branch
(suggested name: `feacher/feat-tc78h653-driver`) after the prerequisites below are settled.

## 1. Goal and scope

- Drive the main motor **directly** with a Toshiba TC78H653FTG dual H-bridge instead of
  through an ESC. The IC is pin controlled (IN1/IN2 or similar); no serial interface was found.
- Keep the current ESC output and make it **selectable by config** (`OUTPUT_DRIVER = 'esc' | 'tc78h653'`),
  so the current behaviour keeps working until the driver board is available.
- Add **reverse** (the protocol currently has Accel and Brake only).
- The steering servo (SG90 / RG50, both 3-wire RC servos) stays on a Pico PWM pin
  (50 Hz, 1000-2000 us). The TC78H653FTG cannot drive an RC servo.

Why the output changes: an ESC takes a pulse **width** (1000-2000 us at 50 Hz). The H-bridge takes a
PWM **duty cycle** (about 20 kHz) plus a direction, so the output code cannot stay in
`control_loop.py` as pulse widths.

## 2. Prerequisites to settle before implementation

Each item names the part of the code it affects. Items 1-4 are hardware facts that only the
hardware owner can confirm.

| # | Prerequisite | Affects |
|---|---|---|
| 1 | **Truth table** of the IC for the chosen MODE / LARGE strapping: forward, reverse, short brake, stop (Hi-Z), standby. The English datasheet PDF could not be read while planning; this plan **assumes the IN1/IN2 scheme with MODE low** (forward = PWM on IN1 and IN2 low, reverse = IN1 low and PWM on IN2, short brake = both high, coast = both low). Confirm or correct it. | `pwm_out.py` only |
| 2 | **Board / module** and its pin names; whether MODE, LARGE and standby are fixed by the board or driven from a Pico GPIO. | `config.py`, `pwm_out.py` |
| 3 | **Motor**: voltage, no-load current and stall current. This decides Small mode (2 A max) or Large mode (4 A max, both bridges in parallel). Large mode leaves no channel for another motor. | wiring, `config.py` |
| 4 | **Supply**: the IC's VM range is about 1.8-7 V (sources disagree: 7.0 V vs 7.5 V; check the datasheet). The measured VSYS is about 6.1 V, close to the limit. A 2S LiPo (8.4 V full) is out of range. Decide the battery / regulator and add a bulk capacitor near VM for back-EMF. | wiring |
| 5 | **Servo power**: a separate 5 V supply (BEC). SG90 is typically 4.8-6 V with a stall current of several hundred mA; never power it from the Pico 3.3 V pin. Check the RG50 voltage range in its datasheet. Common GND for the Pico, the driver and the servo. | wiring |
| 6 | **Pico pins**: neighbouring PWM pins (GP16/GP17, GP18/GP19, ...) share a PWM slice and therefore one frequency. The 20 kHz driver pins (IN1/IN2) and the 50 Hz servo pin must be on **different slices**. Today ESC = GP16 and SERVO = GP17 share a slice, which is fine only while both are 50 Hz. | `config.py` |
| 7 | **Neutral / failsafe state**: coast (both inputs low) or short brake for neutral, failsafe and emergency stop. Proposed: coast, like an RC ESC at neutral; a stopped Pico also leaves the inputs low. | `pwm_out.py`, docs |
| 8 | **PWM frequency**: default 20 kHz (inaudible). Confirm it is below the IC's maximum input frequency. | `config.py` |
| 9 | **Protocol changes** (below) are accepted. | `udp_loop.py`, tools, docs |
| 10 | **Bring-up safety**: first test with the motor disconnected, then with wheels lifted on a current-limited bench supply at low VM. | test procedure |

### Protocol changes (proposed)

- New command **9 = Reverse**, value 0-255. Accel and Reverse are mutually exclusive: each one clears the other.
  Brake still has priority over both.
- Poll reply (24 bytes, big-endian): offset 6 changes from `u16 thr_us` to **`i16 drive`**
  (-255..255, negative = reverse). Flags bit2 = braking. Offset 8 (servo pulse in us) is unchanged.
- In ESC mode `drive` is mapped back to 1000-2000 us (brake and reverse both use the range below neutral, like an RC ESC).

## 3. Design

### `pwm_out.py` (new): output driver
- `EscServoOut`: today's behaviour behind the new interface.
- `Tc78h653Out`: two `machine.PWM` pins (IN1, IN2) at `TC_PWM_FREQ_HZ`,
  `duty_u16 = abs(drive) * 65535 // 255`; forward / reverse / brake / coast per the truth table.
- Both classes: `drive(value, brake)`, `steer_us(us)`, `neutral()`, `deinit()`.
  The servo is a separate 50 Hz PWM pin in both variants.
- `make_output(config)` selects the class from `config.OUTPUT_DRIVER`.

### `control_loop.py`
- Compute a signed `drive` (-255..255) and `brake` (0..255) instead of `thr_us`; the failsafe and
  emergency stop force `drive = 0`, no brake.
- Slew limit: `ACCEL_RESP` units per loop on the forward side (equals today's 2 us per step on a 500 us range).
  Easing off, brake, reverse changes and the failsafe apply immediately.
- Traction control limit applies to the forward throttle only.
- `finally` still calls `neutral()` and `deinit()`.

### Other files
- `shared.py`: add `CMD_REVERSE`; rename `STAT_THR_US` to `STAT_DRIVE`.
- `udp_loop.py`: command 9, new Poll field and flag, status print shows `drive=`.
- `config.py`: `OUTPUT_DRIVER = 'esc'`, `TC_IN1_PIN`, `TC_IN2_PIN`, `TC_PWM_FREQ_HZ = 20000`.
- `tools/udp_client.py`: command 9, decode the signed `drive` and the brake flag.
- `tools/udp_shell.py`: `v100` = reverse (`f`, `b`, `l`, `r` stay as they are).
- `docs/protocol.md`, `docs/system-architecture.md`: command 9, the Poll field, the output driver.

## 4. Implementation steps

Each step is small enough for one commit.

1. Output driver (`pwm_out.py`) with `EscServoOut` only; `control_loop.py` uses it. Regression: behaviour identical to today.
2. Reverse: protocol, loop, Poll field, PC tools.
3. `Tc78h653Out` and the `OUTPUT_DRIVER` switch.
4. Documentation.

## 5. Verification

1. PC: unit checks of the command mapping (forward -> reverse -> brake priority, mutual exclusion,
   signed Poll field decode) against a fake Pico.
2. `OUTPUT_DRIVER = 'esc'` regression: about 1750 us for `f128`, neutral after 500 ms without packets.
3. `OUTPUT_DRIVER = 'tc78h653'`, motor disconnected: with a logic analyzer or scope, IN1 / IN2 show PWM on one
   pin only for `f` / `v`, both high for `b`, both low for `s`, emergency stop and the failsafe; frequency about 20 kHz.
4. Motor connected, wheels lifted, current-limited supply at low VM: the duty follows the command, reverse and brake
   behave, and cutting the UDP traffic stops the motor within about 500 ms.
5. `loop_us` stays around 4167-4400 us.

## 6. Sources

- [Toshiba TC78H653FTG Dual Bridge Driver IC (Mouser)](https://www.mouser.se/toshiba-tc78h653ftg-driver)
- [TC78H653FTG low voltage high current H-bridge motor driver (Components101)](https://components101.com/news/TC78H653FTG-low-voltage-high-current-hbridge-motor-driver)
- [TC78H653FTG datasheet, Japanese (Akizuki Denshi)](https://akizukidenshi.com/goodsaffix/TC78H653FTG_datasheet_ja_20190129.pdf)
- [TC78H653FTG datasheet, English (Toshiba)](https://toshiba.semicon-storage.com/info/datasheet_en_20250311.pdf?did=160167)
