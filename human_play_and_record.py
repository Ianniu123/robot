"""
Controls:
  SPACE or click  -> flap
  Q               -> quit

Frames saved to:  dataset/frame_XXXXX.jpg
"""

import os
import time
import threading
import cv2
import pygame
import gymnasium
import flappy_bird_gymnasium  # registers FlappyBird-v0

GAME_W, GAME_H = 288, 512
SCALE_FACTOR   = 1.5
CAMERA_INDEX   = 0
CAMERA_ZOOM    = 2.0
SAVE_DIR       = "dataset"
SAVE_FPS       = 5

os.makedirs(SAVE_DIR, exist_ok=True)

frame_idx = 0
stop_cam  = threading.Event()

def camera_thread():
    global frame_idx
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print(f"Could not open camera {CAMERA_INDEX}")
        return
    
    interval = 1.0 / SAVE_FPS
    last_save = 0.0

    while not stop_cam.is_set():
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue
        now = time.time()

        if now - last_save >= interval:
            if CAMERA_ZOOM > 1.0:
                h, w = frame.shape[:2]
                ch, cw = int(h / CAMERA_ZOOM), int(w / CAMERA_ZOOM)
                sy, sx = (h - ch) // 2, (w - cw) // 2
                frame = cv2.resize(frame[sy:sy+ch, sx:sx+cw], (w, h))
            cv2.imwrite(os.path.join(SAVE_DIR, f"frame_{frame_idx:05d}.jpg"), frame)
            frame_idx += 1
            last_save = now

        time.sleep(0.005)
    cap.release()

cam_thread = threading.Thread(target=camera_thread, daemon=True)
cam_thread.start()

env = gymnasium.make("FlappyBird-v0", render_mode="rgb_array")
obs, _ = env.reset()

pygame.init()
SCREEN_SIZE = (int(GAME_W * SCALE_FACTOR), int(GAME_H * SCALE_FACTOR))
screen = pygame.display.set_mode(SCREEN_SIZE)
pygame.display.set_caption("Flappy Bird | SPACE=flap | Q=quit")
clock = pygame.time.Clock()

episode = 1
running = True
try:
    while running:
        flap = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_SPACE:
                    flap = True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                flap = True

        obs, _, term, trunc, info = env.step(1 if flap else 0)
        rgb = env.render()
        screen.blit(pygame.transform.scale(
            pygame.surfarray.make_surface(rgb.swapaxes(0, 1)), SCREEN_SIZE), (0, 0))
        pygame.display.flip()

        if term or trunc:
            print(f"Episode {episode} score: {info.get('score', 0)}  frames: {frame_idx}")
            episode += 1
            obs, _ = env.reset()
             
        clock.tick(30)
except KeyboardInterrupt:
    pass
finally:
    stop_cam.set()
    cam_thread.join(timeout=2)
    env.close()
    pygame.quit()
    print(f"Done. {frame_idx} frames saved to '{SAVE_DIR}/'")
