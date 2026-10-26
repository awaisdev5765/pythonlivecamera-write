# 📷 Camera Studio

Draw in the air with your bare hands on a live camera feed — no mouse needed.

![demo](https://img.shields.io/badge/python-3.9%2B-blue) ![opencv](https://img.shields.io/badge/OpenCV-5.0-orange) ![mediapipe](https://img.shields.io/badge/MediaPipe-hand--tracking-green)

## ✨ Features
- **🖐 Air drawing** — point ☝️ with your index finger and write on the live video
- **✌️ Color switching** — flash two fingers to cycle 6 colors (Gold, Amber, Green, Sky, Violet, White)
- **↩️ Undo** (`Z`) — remove the last stroke
- **🖱 Mouse drawing** (`D`) — classic drag-to-draw mode
- **🔤 Text overlays** (`T`) — type text, place it on the video
- **📸 Snapshots** (`S`) — save annotated frames to `snapshots/`
- **⏺️ Recording** (`R`) — record the annotated feed to MP4 in `recordings/`
- **Animated splash screen** + polished HUD with live FPS, timestamp, status chips
- **Async MediaPipe hand tracking** — smooth, full-framerate video
- **Grace period** on gesture transitions so strokes never break mid-write

## 🚀 Quick start
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# download the MediaPipe hand model (~7 MB)
curl -L -o hand_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task

python camera_studio.py
```

## 🎮 Controls
| Gesture / Key | Action |
|---|---|
| ☝️ Point (index up) | Draw |
| ✌️ Two fingers | Next color |
| `Z` | Undo last stroke |
| `D` | Toggle mouse drawing |
| `T` | Type text (Enter to place) |
| `S` | Snapshot |
| `R` | Start/stop recording |
| `C` | Clear all |
| `Q` / `Esc` | Quit |

## 🍎 macOS camera permission
First run: **System Settings → Privacy & Security → Camera** → allow **Python** (or Terminal/PyCharm).

## 📁 Outputs
- `snapshots/` — PNG frames with drawings & text baked in
- `recordings/` — MP4 recordings of the annotated feed
