# Flappy Bird Robot

A robotic arm that physically plays Flappy Bird. A PPO reinforcement learning model watches the game state and commands a SO-101 robot arm to tap the spacebar at the right moment.

---

## Demo Video

<video src="./demo.mp4" controls width="320" height="240"></video>

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│                      gym_demo.py                     │
│                                                      │
│   FlappyBird-v0 gym                                  │
│       ↓ obs                                          │
│   latency compensation                               │
│       ↓                                              │
│   PPO model → arm tap → physical spacebar press      │
│                              ↓                       │
│               pygame KEYDOWN → env.step(flap=1)      │
└─────────────────────────────────────────────────────┘
```

Everything runs in a single process. The PPO model reads the gym's internal state, the arm physically taps the spacebar, and pygame receives the keypress to apply the flap — the arm is the only control input to the game.

---

## Hardware

- **Robot arm**: SO-101 (Feetech STS3215 servos)
- **Connection**: USB serial (`/dev/tty.usbmodem5AAF2196261`)
- **Gripper**: taps the spacebar to flap

---

## Setup

```bash
pip install stable-baselines3 gymnasium flappy-bird-gymnasium pygame lerobot
```

---

## Usage

### Run the demo
```bash
python gym_demo.py                     # full robot
python gym_demo.py --dry-run           # no arm, simulation only
python gym_demo.py --latency-frames 3  # tune arm latency (default: 3)
```

### Arm controller (manual calibration GUI)
```bash
python controller.py
```
Sliders for all 6 joints. **Enable Torque** / **Disable Torque** buttons to toggle servo lock.

---

## Files

| File | Purpose |
|------|---------|
| `gym_demo.py` | Main demo: runs game, reads obs, PPO decides, arm taps |
| `controller.py` | GUI joint controller for manual arm calibration |
| `FlappyBird_stage_final.zip` | PPO model trained on gym observations |

---

## Observation Vector

The model uses a 12-value normalized observation from the gym:

| Index | Name | Description |
|-------|------|-------------|
| 0–2 | last_pipe | x, gap_top, gap_bottom (closest pipe) |
| 3–5 | next_pipe | x, gap_top, gap_bottom |
| 6–8 | nn_pipe | x, gap_top, gap_bottom (furthest visible) |
| 9 | bird_y | vertical position (0 = top, 1 = bottom) |
| 10 | vel_y | vertical velocity / 10 |
| 11 | rot | rotation / 90° |

---

## What I Tried

### Approach 1 — YOLO vision pipeline
Built a full YOLO-based vision system (`main.py`, `vision.py`) that detects the bird and pipes from game frames, reconstructs the observation vector, and feeds it to the PPO model. The robot arm taps based on the model's prediction.

Challenges encountered:
- **Confidence threshold**: YOLO pipe detections had confidence 0.10–0.13, below the 0.15 threshold. Lowering it introduced false positives.
- **Training distribution mismatch**: The original PPO model was trained on perfect gym observations. YOLO observations differ subtly, causing the model to rarely flap.
- **Noise simulation**: Tried training PPO with simulated YOLO noise (30% bird miss rate, 20% pipe miss rate). After 10M steps the model still never learned to flap — dropout was too high to learn from.

### Approach 2 — Direct gym observations (demo)
Bypasses YOLO entirely. `gym_demo.py` reads the gym's internal state directly and feeds it to the PPO model. The robot arm still physically taps the spacebar — no software shortcut to the game. Arm latency is compensated by simulating the bird's physics forward before predicting.

---

## Appendix: Calibration Data

### Joint bounds — follower arm (raw encoder units)

| Joint | Min | Pos | Max |
|-------|-----|-----|-----|
| shoulder_pan | 745 | 2093 | 3489 |
| shoulder_lift | 830 | 849 | 3117 |
| elbow_flex | 824 | 3038 | 3055 |
| wrist_flex | 943 | 2402 | 3246 |
| gripper | 2033 | 2051 | 3565 |

### Joint bounds — leader arm (raw encoder units)

| Joint | Min | Pos | Max |
|-------|-----|-----|-----|
| shoulder_pan | 720 | 2020 | 3441 |
| shoulder_lift | 781 | 792 | 3142 |
| elbow_flex | 869 | 3066 | 3073 |
| wrist_flex | 852 | 2679 | 3180 |
| gripper | 2030 | 2046 | 3294 |

### lerobot setup commands

```bash
lerobot-setup-motors \
    --robot.type=so101_follower \
    --robot.port=/dev/tty.usbmodem5AAF2196261

lerobot-setup-motors \
    --teleop.type=so101_leader \
    --teleop.port=/dev/tty.usbmodem5AAF2195131

lerobot-calibrate \
    --robot.type=so101_follower \
    --robot.port=/dev/tty.usbmodem5AAF2196261 \
    --robot.id=my_awesome_follower_arm

lerobot-calibrate \
    --teleop.type=so101_leader \
    --teleop.port=/dev/tty.usbmodem5AAF2195131 \
    --teleop.id=my_awesome_leader_arm

lerobot-teleoperate \
    --robot.type=so101_follower \
    --robot.port=/dev/tty.usbmodem5AAF2196261 \
    --robot.id=my_awesome_follower_arm \
    --teleop.type=so101_leader \
    --teleop.port=/dev/tty.usbmodem5AAF2195131 \
    --teleop.id=my_awesome_leader_arm
```

### Tap configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| `HOVER_POS` | 2200 | Gripper resting position (above key) |
| `TAP_POS` | 2350 | Gripper extended position (on key) |
| `TAP_DOWN_S` | 0.08s | Time to move down to key |
| `TAP_HOLD_S` | 0.05s | Time to hold key pressed |
| `TAP_UP_S` | 0.08s | Time to return to hover |

Overlapping taps are prevented by a threading lock in `arm.tap()` — if the arm is still mid-motion, the new tap command is silently dropped.

### Latency compensation

Total arm latency ≈ 113ms ≈ 3 game frames (80ms travel + 33ms frame).

`gym_demo.py` simulates physics forward by `--latency-frames` before predicting.

| `--latency-frames` | Symptom if wrong |
|--------------------|-----------------|
| Too low | Bird hits floor — flaps too late |
| Too high | Bird hits ceiling — flaps too early |
