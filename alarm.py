"""
Dance Alarm - the alarm keeps ringing until you dance in front of the camera
for 10 continuous seconds (built with MediaPipe Pose).

Usage:
    python alarm.py 06:30       # ring at 06:30 today (tomorrow if already past)
    python alarm.py --test 15   # ring in 15 seconds (quick test)

While it rings:
    - Camera opens and tracks your body with MediaPipe Pose
    - Your dance "fills the bar"; keep moving for 10 seconds to silence it
    - S = snooze 5 minutes, Q = quit
"""

import argparse
import sys
import threading
import time
from datetime import datetime, timedelta

import cv2
import mediapipe as mp
import numpy as np
import winsound
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

MODEL_PATH = "pose_landmarker_lite.task"

DANCE_TARGET_SECONDS = 10.0
SNOOZE_MINUTES = 5

MOVE_THRESHOLD = 0.07
EMA_ALPHA = 0.35
IDLE_GRACE = 2.0
CAMERA_INDEX = 0

POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8), (9, 10),
    (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24), (23, 25), (24, 26), (25, 27), (26, 28),
    (27, 29), (28, 30), (29, 31), (30, 32),
]


def ring_loop(stop_event):
    while not stop_event.is_set():
        winsound.Beep(1200, 350)
        if stop_event.wait(0.08):
            break
        winsound.Beep(900, 350)
        stop_event.wait(0.08)


def victory_tune():
    for freq, dur in [(523, 150), (659, 150), (784, 150), (1047, 300)]:
        winsound.Beep(freq, dur)


def ring_at(target):
    print(f"Alarm set for {target:%H:%M:%S}. Waiting...")
    while datetime.now() < target:
        remain = (target - datetime.now()).total_seconds()
        print(f"  {int(remain):>4}s left...", end="\r", flush=True)
        time.sleep(min(1, max(0.1, remain)))
    print("\n*** ALARM! TIME TO DANCE! ***")


def dance_check(stop_event):
    """Camera window: returns True if the user danced the full 10 seconds."""
    base = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.PoseLandmarkerOptions(
        base_options=base,
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    landmarker = vision.PoseLandmarker.create_from_options(options)

    cam = cv2.VideoCapture(CAMERA_INDEX)
    if not cam.isOpened():
        print("ERROR: could not open the camera.")
        return "quit"

    prev_lms = None
    smooth_score = 0.0
    progress = 0.0
    idle_time = 0.0
    last_ts = None
    prev_frame_time = None
    outcome = "quit"

    try:
        while not stop_event.is_set():
            ok, frame = cam.read()
            if not ok:
                time.sleep(0.05)
                continue

            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            now_ms = int(time.perf_counter() * 1000)
            if last_ts is None:
                last_ts = now_ms - 1
            last_ts = max(last_ts + 1, now_ms - 30)
            frame_time = time.perf_counter()
            if prev_frame_time is None:
                dt = 1 / 30
            else:
                dt = min(0.2, max(1 / 120, frame_time - prev_frame_time))
            prev_frame_time = frame_time

            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB,
                              data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            result = landmarker.detect_for_video(mp_img, last_ts)

            score = 0.0
            if result.pose_landmarks:
                lms = result.pose_landmarks[0]
                pts = np.array([[lm.x, lm.y] for lm in lms])
                scale = max(1e-3, np.linalg.norm(pts[11] - pts[12]))
                if prev_lms is not None and prev_lms.shape == pts.shape:
                    disp = np.linalg.norm(pts - prev_lms, axis=1).mean()
                    score = disp / scale
                prev_lms = pts

                for a, b in POSE_CONNECTIONS:
                    pa = (int(pts[a][0] * w), int(pts[a][1] * h))
                    pb = (int(pts[b][0] * w), int(pts[b][1] * h))
                    cv2.line(frame, pa, pb, (0, 255, 0), 2)
                for p in pts:
                    cv2.circle(frame, (int(p[0] * w), int(p[1] * h)), 4, (255, 255, 255), -1)
                present = True
            else:
                prev_lms = None
                present = False

            smooth_score = EMA_ALPHA * score + (1 - EMA_ALPHA) * smooth_score
            dancing = present and smooth_score > MOVE_THRESHOLD

            if dancing:
                progress = min(DANCE_TARGET_SECONDS, progress + dt)
                idle_time = 0.0
            else:
                idle_time += dt
                if idle_time > IDLE_GRACE:
                    progress = max(0.0, progress - dt * 2.0)

            # ---- HUD ----
            cv2.putText(frame, "ALARM! GET UP AND DANCE!", (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)

            bar_w, bar_h = w - 80, 40
            x0, y0 = 40, h - bar_h - 40
            cv2.rectangle(frame, (x0, y0), (x0 + bar_w, y0 + bar_h), (255, 255, 255), 2)
            fill = int(bar_w * progress / DANCE_TARGET_SECONDS)
            cv2.rectangle(frame, (x0, y0), (x0 + fill, y0 + bar_h), (0, 220, 0), -1)
            cv2.putText(frame, f"DANCE {progress:0.1f}s / {DANCE_TARGET_SECONDS:.0f}s",
                        (x0 + 10, y0 + int(bar_h * 0.7)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

            state = "MOVING!" if dancing else ("stand by..." if present else "no person detected")
            color = (0, 255, 0) if dancing else (0, 165, 255)
            cv2.putText(frame, state, (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.putText(frame, "S = snooze | Q = quit", (20, 130),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

            cv2.imshow("Dance Alarm - dance for 10s to stop it!", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                outcome = "quit"
                break
            if key == ord("s"):
                stop_event.set()
                outcome = "snooze"
                break

            if progress >= DANCE_TARGET_SECONDS:
                outcome = "success"
                break
    finally:
        cam.release()
        cv2.destroyAllWindows()
        landmarker.close()
    return outcome


def run_alarm():
    parser = argparse.ArgumentParser(description="Alarm that stops when you dance.")
    parser.add_argument("time", nargs="?", default=None, help="alarm time HH:MM (24h)")
    parser.add_argument("--test", type=float, default=None, metavar="SEC",
                        help="ring after SEC seconds (test mode)")
    args = parser.parse_args()

    if args.test is not None:
        target = datetime.now() + timedelta(seconds=args.test)
    elif args.time:
        hh, mm = map(int, args.time.split(":"))
        target = datetime.now().replace(hour=hh, minute=mm, second=0, microsecond=0)
        if target <= datetime.now():
            target += timedelta(days=1)
    else:
        target = datetime.now() + timedelta(minutes=1)
        print("No time given - defaulting to 1 minute from now (--test N also works).")

    snooze = 0
    while True:
        if snooze:
            print(f"Snoozing for {SNOOZE_MINUTES} minutes...")
            time.sleep(SNOOZE_MINUTES * 60)
            snooze = 0
        ring_at(target)

        stop_event = threading.Event()
        t = threading.Thread(target=ring_loop, args=(stop_event,), daemon=True)
        t.start()
        try:
            res = dance_check(stop_event)
        finally:
            stop_event.set()

        if res == "success":
            print("Dance detected for 10 seconds - ALARM SILENCED. Good morning!")
            victory_tune()
            break
        print("Snoozing (or quit).")
        target = datetime.now() + timedelta(minutes=SNOOZE_MINUTES)
        snooze = 1


if __name__ == "__main__":
    run_alarm()
