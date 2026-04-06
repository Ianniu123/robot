import argparse
import threading
import time

import numpy as np
import pygame
import gymnasium
import flappy_bird_gymnasium
from stable_baselines3 import PPO

# ── Config ────────────────────────────────────────────────────────────────────

ARM_PORT        = "/dev/tty.usbmodem5AAF2196261"
HOVER_POS       = 2200
TAP_POS         = 2350
TAP_DOWN_S      = 0.08
TAP_HOLD_S      = 0.05
TAP_UP_S        = 0.08

GAME_FPS       = 30
PLAYER_GRAVITY = 1
PLAYER_MAX_VEL = 10
GAME_H         = 512
PIPE_VEL_NORM  = 4.0 * GAME_FPS / 288.0

PPO_MODEL = "FlappyBird_stage_final.zip"
SCALE     = 1.5

# ── Arm ───────────────────────────────────────────────────────────────────────

class RawMotor:
    def __init__(self, mid, model): self.id, self.model = mid, model

MOTORS = {
    "shoulder_pan":  RawMotor(1, "sts3215"),
    "shoulder_lift": RawMotor(2, "sts3215"),
    "elbow_flex":    RawMotor(3, "sts3215"),
    "wrist_flex":    RawMotor(4, "sts3215"),
    "wrist_roll":    RawMotor(5, "sts3215"),
    "gripper":       RawMotor(6, "sts3215"),
}

class Arm:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.bus     = None
        self._lock   = threading.Lock()

    def connect(self):
        if self.dry_run:
            print("DRY-RUN: arm disabled")
            return
        from lerobot.motors.feetech import FeetechMotorsBus
        self.bus = FeetechMotorsBus(port=ARM_PORT, motors=MOTORS)
        self.bus.connect()
        for name in MOTORS:
            self.bus.write("Torque_Enable", name, 1, normalize=False)
            if name == "gripper":
                self.bus.write("Goal_Position", name, HOVER_POS, normalize=False)
        time.sleep(1.0)
        print("Arm ready.")

    def tap(self):
        # If the arm is in the middle of tapping then just return
        if self.dry_run or not self._lock.acquire(blocking=False):
            return
        
        threading.Thread(target=self._do_tap, daemon=True).start()

    def _do_tap(self):
        try:
            self.bus.write("Goal_Position", "gripper", TAP_POS,   normalize=False)
            time.sleep(TAP_DOWN_S + TAP_HOLD_S)
            self.bus.write("Goal_Position", "gripper", HOVER_POS, normalize=False)
            time.sleep(TAP_UP_S)
        finally:
            self._lock.release()

    def relax(self):
        pass


# ── Latency compensation ─────────────────────────────────────────────────────
def obs_at_flap_time(obs, latency_frames):
    """Simulate bird physics forward by latency_frames"""
    
    obs = obs.copy()
    vel_pix  = obs[10] * PLAYER_MAX_VEL
    bird_pix = obs[9]  * GAME_H
    for _ in range(latency_frames):
        vel_pix  = min(vel_pix + PLAYER_GRAVITY, PLAYER_MAX_VEL)
        bird_pix = bird_pix + vel_pix
    obs[9]  = float(np.clip(bird_pix / GAME_H, 0.0, 1.0))
    obs[10] = vel_pix / PLAYER_MAX_VEL
    dt = latency_frames / GAME_FPS
    for i in (0, 3, 6):
        if obs[i] < 0.95:
            obs[i] -= PIPE_VEL_NORM * dt
    return obs


# ── Main ──────────────────────────────────────────────────────────────────────

def main(args):
    print(f"Loading model: {PPO_MODEL}")
    ppo = PPO.load(PPO_MODEL, custom_objects={
        "learning_rate": 2.5e-4, "clip_range": 0.15,
        "lr_schedule":   lambda _: 2.5e-4,
    })

    arm = Arm(args.dry_run)
    arm.connect()

    latency_frames = args.latency_frames
    print(f"Latency compensation: {latency_frames} frames "
          f"({latency_frames / GAME_FPS * 1000:.0f}ms)")

    W, H = int(288 * SCALE), int(512 * SCALE)
    env  = gymnasium.make("FlappyBird-v0", render_mode="rgb_array")

    pygame.init()
    screen  = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Flappy Bird Robot")
    clock   = pygame.time.Clock()

    episode = 0
    taps    = 0

    try:
        while True:
            obs, _ = env.reset()
            episode += 1
            done    = False
            flap    = 0

            while not done:
                # Handle pygame events — arm tap sends physical spacebar
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        raise KeyboardInterrupt
                    elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                        flap = 1

                obs, _, term, trunc, info = env.step(flap)
                flap = 0
                done = term or trunc

                # Model decides whether to tap — lock in arm.tap() prevents overlap
                action = int(ppo.predict(
                    obs_at_flap_time(obs, latency_frames),
                    deterministic=True
                )[0])
                if action == 1:
                    arm.tap()
                    taps += 1

                # Render
                rgb = env.render()
                if rgb is not None:
                    surf = pygame.transform.scale(
                        pygame.surfarray.make_surface(rgb.swapaxes(0, 1)), (W, H))
                    screen.blit(surf, (0, 0))
                    pygame.display.flip()

                clock.tick(GAME_FPS)

            print(f"Episode {episode}  score: {info.get('score', 0)}")

    except KeyboardInterrupt:
        pass
    finally:
        env.close()
        pygame.quit()
        arm.relax()
        print(f"Done. {taps} taps.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true",
                   help="No arm, simulation only")
    p.add_argument("--latency-frames", type=int,
                   default=int(round((TAP_DOWN_S + 1.0 / GAME_FPS) * GAME_FPS)),
                   help="Frames to look ahead for arm latency (default: %(default)s)")
    main(p.parse_args())
