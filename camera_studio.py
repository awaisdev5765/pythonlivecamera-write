#!/usr/bin/env python3
"""
Camera Studio — live camera with drawing, text overlays, snapshots & recording.
Animated splash screen → permission screen (if needed) → live studio.
"""
import math
import math
import os
import subprocess
import time

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core import base_options as mp_base

BASE = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_DIR = os.path.join(BASE, "snapshots")
RECORD_DIR = os.path.join(BASE, "recordings")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
os.makedirs(RECORD_DIR, exist_ok=True)

WIDTH, HEIGHT, FPS = 1280, 720, 30
FONT = cv2.FONT_HERSHEY_DUPLEX
WINDOW = "Camera Studio"

INK = (245, 247, 250)
MUTED = (150, 165, 180)
ACCENT = (255, 200, 90)          # gold accent
DANGER = (90, 110, 255)
PANEL = (18, 20, 26)
PANEL_A = 0.72
BTN_BLUE = (251, 111, 31)
BG = (14, 17, 22)
BRAND = "CAMERA  STUDIO"

MODEL = os.path.join(BASE, "hand_landmarker.task")
MODEL = os.path.join(BASE, "hand_landmarker.task")
SMOOTH = 0.4           # fingertip smoothing
PALETTE = [(255, 200, 90), (60, 210, 255), (120, 220, 100), (90, 200, 255),
           (160, 120, 255), (245, 247, 250)]
COLOR_NAMES = ["GOLD", "AMBER", "GREEN", "SKY", "VIOLET", "WHITE"]

HELP = "Point ☝ to draw · ✌ color · D mouse · T text · S snap · R rec · C clear · Q quit"


def fingers_up(lm):
    """(index, middle, ring, pinky) booleans — fingertip above its PIP joint."""
    pairs = [(8, 6), (12, 10), (16, 14), (20, 18)]
    return [lm[tip].y < lm[pip].y - 0.04 for tip, pip in pairs]

HELP = "H Hand-draw   D Mouse-draw   T Text   S Snapshot   R Record   C Clear   Q Quit"


def make_hand_detector(on_result=None):
    opts = vision.HandLandmarkerOptions(
        base_options=mp_base.BaseOptions(model_asset_path=MODEL),
        running_mode=vision.RunningMode.LIVE_STREAM,
        num_hands=1,
        min_hand_detection_confidence=0.6,
        min_tracking_confidence=0.6,
        result_callback=on_result,
    )
    return vision.HandLandmarker.create_from_options(opts)


def stamp():
    return time.strftime("%Y-%m-%d  %H:%M:%S")


def try_camera():
    """One short-lived probe. Returns (cap, ok)."""
    cap = cv2.VideoCapture(0)
    ok = cap.isOpened()
    frame = None
    if ok:
        ok, frame = cap.read()
        if not ok:
            cap.release()
            return None, False
    else:
        cap.release()
        return None, False
    return cap, True


def open_camera_settings():
    subprocess.Popen(["open",
        "x-apple.systempreferences:com.apple.preference.security?Privacy_Camera"])


# ────────────────────────────────────────────────────────────────
# UI helpers
# ────────────────────────────────────────────────────────────────
def rounded(img, x, y, w, h, color, thick=-1):
    cv2.rectangle(img, (x, y), (x + w, y + h), color, thick, cv2.LINE_AA)


def glass(img, x, y, w, h, alpha=PANEL_A):
    ov = img.copy()
    rounded(ov, x, y, w, h, PANEL)
    cv2.addWeighted(ov, alpha, img, 1 - alpha, 0, img)
    rounded(img, x, y, w, h, (60, 66, 76), 1)


def put(img, text, x, y, s=0.7, c=INK, t=1):
    cv2.putText(img, text, (x, y), FONT, s, c, t, cv2.LINE_AA)


def text_w(text, s=0.7, t=1):
    (w, _), _ = cv2.getTextSize(text, FONT, s, t)
    return w


def center(img, text, y, s=0.7, c=INK, t=1):
    put(img, text, (img.shape[1] - text_w(text, s, t)) // 2, y, s, c, t)


def chip(img, x, y, text, color):
    w = text_w(text, 0.5) + 18
    rounded(img, x, y, w, 26, color)
    put(img, text, x + 9, y + 18, 0.5, (15, 15, 15))
    return w


# ────────────────────────────────────────────────────────────────
# Splash screen — animated branding + loading bar while camera warms up
# ────────────────────────────────────────────────────────────────
def splash_progress(canvas, label, progress, t):
    h, w = canvas.shape[:2]
    cx = w // 2

    # soft glow behind the logo dot
    for r, a in ((120, 0.10), (80, 0.16)):
        glow = canvas.copy()
        cv2.circle(glow, (cx, h // 2 - 60), r, (40, 30, 10), -1, cv2.LINE_AA)
        cv2.addWeighted(glow, a, canvas, 1 - a, 0, canvas)

    # pulsing aperture logo
    pulse = 4 + 3 * math.sin(t * 4)
    cv2.circle(canvas, (cx, h // 2 - 60), 40, ACCENT, 2, cv2.LINE_AA)
    cv2.circle(canvas, (cx, h // 2 - 60), int(12 + pulse), ACCENT, -1, cv2.LINE_AA)
    cv2.circle(canvas, (cx, h // 2 - 60), 26, (80, 70, 40), 1, cv2.LINE_AA)

    center(canvas, BRAND, h // 2 + 10, 1.0, INK, 2)
    center(canvas, "by you  ·  powered by OpenCV", h // 2 + 42, 0.45, MUTED)

    # loading bar
    bw, bh = 360, 8
    bx, by = cx - bw // 2, h // 2 + 80
    rounded(canvas, bx, by, bw, bh, (60, 66, 76), 1)
    fill = int(bw * progress)
    if fill > 0:
        rounded(canvas, bx, by, fill, bh, ACCENT)
    # moving shine
    shine = (bx + int((t * 300) % (bw + 60))) - 30
    cv2.rectangle(canvas, (shine, by), (shine + 30, by + bh), (255, 255, 255), -1)

    center(canvas, label, h // 2 + 130, 0.55, ACCENT)


def splash_then_camera():
    """Animated splash while probing the camera (max ~4s)."""
    cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
    canvas = np.zeros((HEIGHT, WIDTH, 3), np.uint8)
    canvas[:] = BG

    phases = ["INITIALIZING CAMERA…", "WARMING UP SENSOR…", "ALMOST READY…"]
    t0 = time.time()
    while True:
        t = time.time() - t0
        phase_idx = min(int(t / 1.4), len(phases) - 1)
        phase = min(t / 4.0, 1.0)
        splash_progress(canvas, phases[phase_idx], min(t / 4.0, 1.0), t)
        cv2.imshow(WINDOW, canvas)
        if cv2.waitKey(33) & 0xFF in (ord("q"), 27):
            return None
        cap, ok = try_camera()
        if ok:
            return cap
        if t >= 4.0:
            return None


# ────────────────────────────────────────────────────────────────
# Permission screen — in-window, with clickable buttons
# ────────────────────────────────────────────────────────────────
def permission_screen():
    W, H = 900, 560
    canvas = np.zeros((H, W, 3), np.uint8)
    canvas[:] = BG

    btn = {"settings": (W // 2 - 190, 400, 380, 56),
           "retry": (W // 2 - 110, 478, 220, 48)}

    def draw():
        canvas[:] = BG
        cv2.circle(canvas, (W // 2, 120), 46, (20, 27, 34), -1, cv2.LINE_AA)
        cv2.circle(canvas, (W //  2, 120), 46, DANGER, 2, cv2.LINE_AA)
        put(canvas, "!", W // 2 - 7, 132, 1.2, DANGER, 2)
        center(canvas, "Camera Access Blocked", 210, 1.0, INK, 2)
        for i, line in enumerate(["macOS has not granted camera access to Camera Studio.",
                                  "Enable access in Privacy & Security, then press Retry."]):
            center(canvas, line, 250 + i * 30, 0.55, MUTED)

        x, y, w, h = btn["settings"]
        cv2.rectangle(canvas, (x, y), (x + w, y + h), BTN_BLUE, -1, cv2.LINE_AA)
        t = "Open Privacy && Security  →"
        put(canvas, t, x + (w - text_w(t, 0.7)) // 2, y + 35, 0.7, (255, 255, 255), 2)

        x, y, w, h = btn["retry"]
        cv2.rectangle(canvas, (x, y), (x + w, y + h), BTN_GREY := (38, 43, 52), -1, cv2.LINE_AA)
        t = "Retry Camera"
        put(canvas, t, x + (w - text_w(t, 0.7)) // 2, y + 35, 0.7, INK, 1)

        center(canvas, "Tip: press Allow on the macOS prompt if it appears.", H - 20, 0.42, (110, 118, 129))

    def on_mouse(event, x, y, *_):
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        for name in ("settings", "retry"):
            bx, by, bw, bh = btn[name]
            if bx <= x <= bx + bw and by <= y <= by + bh:
                if name == "settings":
                    open_camera_settings()
                break

    cv2.setMouseCallback(WINDOW, on_mouse)

    poll_t = 0.0
    while True:
        draw()
        cv2.imshow(WINDOW, canvas)
        k = cv2.waitKey(150) & 0xFF
        if k in (ord("q"), 27):
            return None
        # light-weight authorization poll every 1.5 s
        if time.time() - poll_t > 1.5:
            poll_t = time.time()
            cap, ok = try_camera()
            if ok:
                return cap


# ────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────
def main():
    cap = splash_then_camera()
    if cap is None:
        cap = permission_screen()
        if cap is None:
            return

    cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)

    draw_mode = drawing = False
    points, current = [], []
    text_overlays, typing = [], None
    stroke_color, stroke_width = PALETTE[0], 4
    rec_path = writer = None
    recording = False
    status = "Welcome — press D to draw on the video"
    frames, t0, fps_now = 0, time.time(), 0.0

    # ---- hand detector (async LIVE_STREAM → smoothest tracking) ----
    latest = []  # [ (hand_landmarks, ts_ms) ] filled by callback

    def on_result(result, output_img, ts_ms):
        latest.clear()
        latest.append(result)

    hand_det = None
    if os.path.exists(MODEL):
        try:
            hand_det = make_hand_detector(on_result)
        except Exception as e:
            print("Hand detector unavailable:", e)

    # ---- hand tracking state (auto-detect, no key needed) ----
    hand_on = hand_det is not None
    last_ts = None
    tip = None                 # smoothed index fingertip (px)
    pen_down = False
    hand_pts = []              # current finger stroke
    color_idx, last_color_t = 0, 0.0
    pointing_lost = 0.0       # grace timer for gesture transitions
    status = "Show your hand — pinch to draw" if hand_on else "Press D to draw with mouse"

    def on_mouse(event, x, y, flags, param):
        nonlocal drawing, current
        if not draw_mode:
            return
        if event == cv2.EVENT_LBUTTONDOWN:
            drawing, current = True, [(x, y)]
        elif event == cv2.EVENT_MOUSEMOVE and drawing:
            current.append((x, y))
        elif event == cv2.EVENT_LBUTTONUP and drawing:
            drawing = False
            if len(current) > 1:
                points.append((list(current), stroke_color, stroke_width))
            current = []

    cv2.setMouseCallback(WINDOW, on_mouse)

    def render(frame):
        h, w = frame.shape[:2]
        out = frame.copy()

        for pts, color, width in points:
            cv2.polylines(out, [np.array(pts, np.int32)], False, color, width, cv2.LINE_AA)
        if current:
            cv2.polylines(out, [np.array(current, np.int32)], False, stroke_color, stroke_width, cv2.LINE_AA)
        if hand_pts and len(hand_pts) > 1:   # live finger stroke, rendered in real time
            cv2.polylines(out, [np.array(hand_pts, np.int32)], False, stroke_color, stroke_width, cv2.LINE_AA)

        for text, tx, ty in text_overlays:
            cv2.putText(out, text, (tx + 2, ty + 2), FONT, 1.0, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(out, text, (tx, ty), FONT, 1.0, (0, 230, 255), 2, cv2.LINE_AA)

        # top HUD
        glass(out, 16, 16, w - 32, 46)
        put(out, "●", 30, 46, 0.7, DANGER if recording else (120, 130, 140), 2)
        put(out, stamp(), 56, 46, 0.62, INK)
        put(out, f"{fps_now:4.0f} FPS", 300, 46, 0.62, MUTED)
        cx = 410
        cx += chip(out, cx, 26, "REC" if recording else "LIVE",
                   DANGER if recording else (40, 160, 90)) + 8
        if draw_mode:
            cx += chip(out, cx, 26, "DRAW", (30, 140, 240)) + 8
        if hand_on and tip is not None:
            cv2.circle(out, (int(tip[0]), int(tip[1])), 11, stroke_color, 2, cv2.LINE_AA)
            if pen_down:
                cv2.circle(out, (int(tip[0]), int(tip[1])), 5, stroke_color, -1, cv2.LINE_AA)
            # palette swatches in HUD
            for i, c in enumerate(PALETTE):
                x0 = cx + i * 30
                cv2.rectangle(out, (x0, 26), (x0 + 22, 48), c, -1, cv2.LINE_AA)
                if i == color_idx:
                    cv2.rectangle(out, (x0 - 2, 24), (x0 + 24, 50), INK, 2, cv2.LINE_AA)
        put(out, BRAND, w - text_w(BRAND, 0.62) - 30, 46, 0.62, MUTED)

        if typing is not None:
            glass(out, 16, 74, w - 32, 44)
            put(out, "TEXT:", 32, 102, 0.6, ACCENT)
            put(out, (typing + "▌") if typing else "type…▌", 100, 102, 0.85, INK)

        bar_h = 54
        glass(out, 16, h - bar_h - 16, w - 32, bar_h)
        y = h - bar_h + 11
        put(out, status, 30, y, 0.55, ACCENT)
        put(out, HELP, w - text_w(HELP, 0.5) - 30, y, 0.5, MUTED)
        return out

    while True:
        ok, frame = cap.read()
        if not ok:
            status = "Camera lost — trying to recover…"
            cap.release()
            time.sleep(0.5)
            cap, ok2 = try_camera()
            if not ok2:
                print("Camera read failed — is another app using the camera?")
                break
            continue

        # ---- automatic hand tracking (async detection + gesture logic) ----
        if hand_on:
            small = cv2.resize(frame, (640, 360))
            rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            ts = time.monotonic_ns() // 1_000_000
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            try:
                hand_det.detect_async(mp_img, ts)
            except Exception:
                pass  # transient model hiccup — keep last result

            h, w = frame.shape[:2]
            res = latest[0] if latest else None
            if res is not None and res.hand_landmarks:
                lm = res.hand_landmarks[0]
                idx, thb = lm[8], lm[4]           # index tip, thumb tip
                f = fingers_up(lm)
                n_up = sum(f)

                # gesture: point (index up, middle down) = draw
                pointing = f[0] and not f[1]
                # gesture: two fingers (index+middle) = cycle color, debounced
                if f[0] and f[1] and (time.time() - last_color_t) > 0.8:
                    color_idx = (color_idx + 1) % len(PALETTE)
                    stroke_color = PALETTE[color_idx]
                    last_color_t = time.time()
                    status = f"Color → {COLOR_NAMES[color_idx]}"

                # mirrored, smoothed fingertip position
                raw = (w * (1 - idx.x), h * idx.y)
                tip = raw if tip is None else (SMOOTH * tip[0] + (1 - SMOOTH) * raw[0],
                                               SMOOTH * tip[1] + (1 - SMOOTH) * raw[1])

                if pointing and not pen_down:
                    pen_down = True
                    hand_pts = [(int(tip[0]), int(tip[1]))]
                    pointing_lost = 0.0
                elif pen_down and pointing:
                    pointing_lost = 0.0
                    # adaptive min-segment length based on hand size (distance-stable)
                    hand_size = math.hypot(lm[0].x - lm[9].x, lm[0].y - lm[9].y)
                    min_len = max(4, int(hand_size * w * 0.10))
                    px, py = hand_pts[-1]
                    if (tip[0] - px) ** 2 + (tip[1] - py) ** 2 >= min_len ** 2:
                        hand_pts.append((int(tip[0]), int(tip[1])))
                elif pen_down and not pointing:
                    # grace period: brief gesture flickers don't cut the stroke
                    if pointing_lost == 0.0:
                        pointing_lost = time.time()
                    elif time.time() - pointing_lost > 0.18:
                        pen_down = False
                        if len(hand_pts) > 1:
                            points.append((list(hand_pts), stroke_color, stroke_width))
                        hand_pts = []
                        pointing_lost = 0.0
            else:
                if pen_down and len(hand_pts) > 1:
                    points.append((list(hand_pts), stroke_color, stroke_width))
                pen_down, hand_pts, tip = False, [], None
                pointing_lost = 0.0

        out = render(frame)
        if recording and writer is not None:
            writer.write(out)

        cv2.imshow(WINDOW, out)
        key = cv2.waitKey(1) & 0xFF

        if key in (ord("q"), 27):
            break
        elif key == ord("d"):
            draw_mode = not draw_mode
            status = "Drawing ON — drag on the video" if draw_mode else "Drawing off"
        elif key == ord("t"):
            typing, status = "", "Type text — Enter to place, Esc to cancel"
            while True:
                ok2, f2 = cap.read()
                if ok2:
                    cv2.imshow(WINDOW, render(f2))
                k = cv2.waitKey(30) & 0xFF
                if k in (13, 10):
                    if typing.strip():
                        ty = 130 + 46 * len(text_overlays)
                        if ty > f2.shape[0] - 160:
                            text_overlays.clear(); ty = 130
                        text_overlays.append((typing, 60, ty))
                    typing, status = None, "Text placed"
                    break
                if k == 27:
                    typing, status = None, "Text cancelled"
                    break
                if k == 8:
                    typing = typing[:-1]
                elif 32 <= k < 127:
                    typing += chr(k)
        elif key == ord("s"):
            path = os.path.join(SNAPSHOT_DIR, f"shot_{time.strftime('%Y%m%d_%H%M%S')}.png")
            cv2.imwrite(path, out)
            status = f"Snapshot saved → {os.path.basename(path)}"
        elif key == ord("z"):
            if points:
                points.pop()
                status = "Undo — stroke removed"
        elif key == ord("c"):
            points.clear(); text_overlays.clear()
            status = "Canvas cleared"
        elif key == ord("r"):
            if not recording:
                rec_path = os.path.join(RECORD_DIR, f"rec_{time.strftime('%Y%m%d_%H%M%S')}.mp4")
                writer = cv2.VideoWriter(rec_path, cv2.VideoWriter_fourcc(*"mp4v"),
                                         FPS, (out.shape[1], out.shape[0]))
                recording = True
                status = f"Recording → {os.path.basename(rec_path)}"
            else:
                recording = False
                writer.release(); writer = None
                status = f"Recording saved → {os.path.basename(rec_path)}"

        frames += 1
        if time.time() - t0 >= 1.0:
            fps_now = frames / (time.time() - t0)
            frames, t0 = 0, time.time()

    if writer is not None:
        writer.release()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
