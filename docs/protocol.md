# Network protocol(UDP Binary)

## 1byte

- 1=Accel
- 2=Steering
- 3=Break
- 4=Poling
- 5=System Stop
- 6=System Reset
- 7=Emergency stop
- 8=Setting

## 2byte

- 1=Accel：
  slotle value:0~256

- 2=Steering:
  servo : 0~180 (90がセンター)
- 3=Break
  break value:0~256

- 4=Poling: None
- 5=System Stop: None
- 6=System Reset: None
- 7=Emergency stop: None

- 8=Setting
  1= Steering offset degrees
  2= Accel responce
  3= Traction control level

## 3byte (8=Setting Only)

- 1= Steering offset degrees -20~20
- 2= Accel responce 1~10
- 3= Traction control level 1~10

3byte は符号付き int8（-128〜127）として解釈し、範囲外はクランプする。

## 実装上の取り決め

- 受信ポート: `config.UDP_PORT`（既定 5000）
- Accel / Break は 1byte のため実際の範囲は **0〜255**（256 は送れない）
- Break > 0 のときは Accel より Break を優先する
- 長さ不足・未知のコマンドは捨てる（キープアライブ扱いにもしない）
- **フェイルセーフ**: 有効なパケットが `config.FAILSAFE_MS`（既定 500ms）途絶えると、スロットルはニュートラル、ステアは中央になる。コマンドを送らない間は Poling(4) をキープアライブとして送り続けること
- **Emergency stop(7)** はラッチ。System Reset(6) まで出力はニュートラルのまま
- System Stop(5): 制御ループと UDP ループを停止する（出力はニュートラル）
- System Reset(6): 出力をニュートラルにしてから `machine.reset()`

## Poling(4) 応答

送信元アドレスへ 24byte を返す（リトルエンディアン、`struct` 形式 `<BBBBBBHHhhhhHhh`）。

| offset | 型 | 内容 |
|--------|----|------|
| 0 | u8 | `0x84`（4 への応答） |
| 1 | u8 | flags: bit0=failsafe, bit1=emergency stop |
| 2 | u8 | Accel 指令値 0〜255 |
| 3 | u8 | Steering 指令値 0〜180 |
| 4 | u8 | Break 指令値 0〜255 |
| 5 | u8 | Traction control level |
| 6 | u16 | ESC 出力パルス (us) |
| 8 | u16 | サーボ出力パルス (us) |
| 10 | i16 | accel X (mg) |
| 12 | i16 | accel Y (mg) |
| 14 | i16 | accel Z (mg) |
| 16 | i16 | gyro Z (0.1 dps) |
| 18 | u16 | 制御ループ周期 (us)、240Hz なら約 4167 |
| 20 | i16 | roll (0.01°)。加速度とジャイロの相補フィルタ |
| 22 | i16 | pitch (0.01°) |

加速度・ジャイロはセンサーの取り付け向きを `config.IMU_AXIS_MAP` で車体座標（X=前、Y=左、Z=上。加速度は上向きの軸が + になる）に変換した値。右に傾く（右側が下がる）と左が上がるので ay > 0、roll > 0。前が下がると ax < 0、pitch > 0。roll と pitch の値を入れ替えたいときは `config.ATTITUDE_SWAP_ROLL_PITCH`（既定 True）。

roll = `atan2(ay, az)`、pitch = `atan2(-ax, sqrt(ay²+az²))` を基準にする。符号は実機で確認して確定する（逆なら `config.ATTITUDE_ROLL_SIGN` / `ATTITUDE_PITCH_SIGN` で反転）。yaw は地磁気センサーがなくドリフトするため出さない。
