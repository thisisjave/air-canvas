# Air Canvas — Changelog & Upgrades

A complete log of all changes and upgrades made to the Air Canvas project, from initial prototype to the current Phase 2 MediaPipe-powered version.

---

## Phase 2: MediaPipe Hand Tracking (Current)
> *Branch: `phase-2`*

### 🧠 Core Engine Migration
- **Replaced** HSV color-based tracking with **Google MediaPipe Hand Landmarker** (Deep Learning).
- **Eliminated** the need for `picker.py` calibration — the system now works in any lighting, with any background, using bare hands.
- **Adopted** the new **MediaPipe Tasks API** (`mp.tasks.vision.HandLandmarker`) compatible with MediaPipe v0.10.31+.
- **Downloaded** the official `hand_landmarker.task` model (float16, 7.6MB) for on-device inference.

### ✋ Gesture-Based Control System
- **1 Finger Up (Index only)** → Drawing Mode (ink follows fingertip).
- **2 Fingers Up (Index + Middle)** → Hovering Mode (cursor moves, no ink).
- Gesture detection uses **landmark Y-coordinate comparison** (fingertip vs. PIP joint) for reliable finger-up detection.
- Gestures are easily swappable — can be changed to Pinch, Open Palm, etc.

### 🎯 1 Euro Filter (Replaced Kalman + EMA)
- **Created** `euro_filter.py` — a self-contained implementation of the [1€ Filter](https://cristal.univ-lille.fr/~casiez/1euro/) algorithm.
- **Adaptive smoothing**: Automatically uses heavy smoothing during slow hand movements (eliminates tremors) and light smoothing during fast movements (preserves responsiveness).
- **Tuned parameters**: `min_cutoff=0.3`, `beta=0.02` for optimal balance between smoothness and lag.
- **Anti-aliased rendering**: Lines are now drawn with `cv2.LINE_AA` for sub-pixel smooth edges.

### 📷 Camera Identification Tool
- **Upgraded** `test_cameras.py` into a **visual camera selector** that shows labeled live previews from each camera index with resolution info.
- Helps identify iPhone Continuity Camera vs. MacBook built-in camera.

---

## Phase 1: HSV Color Tracking (Foundation)
> *Branch: `main`*

### 🎨 Core Drawing Engine
- Built a real-time drawing application using **OpenCV** and **NumPy**.
- Implemented **persistent canvas** (`imgCanvas`) using a NumPy array for stable stroke rendering.
- Replaced discrete dot rendering with **continuous `cv2.line` segments** between frames.

### 🔬 Kalman Filter Smoothing
- Integrated a **2D Kalman Filter** (`cv2.KalmanFilter`) to predict pen velocity and smooth coordinates.
- Implemented **state-reset logic** on new strokes to prevent "lag" or "jump" artifacts.
- Tuned `processNoiseCov` from `0.2` → `0.05` for maximum stability.

### 📊 Exponential Moving Average (EMA)
- Added EMA (`α = 0.5`) as a secondary smoothing layer on top of Kalman predictions.
- Provides "electronic shock absorption" for minor hand tremors.

### 🔧 Noise Reduction Pipeline
- **Gaussian Blur** (`5x5`) applied to raw camera frames to reduce sensor noise.
- **Morphological Opening** (Erode + Dilate) cleans the HSV mask of small noise dots.
- **Outlier Rejection**: 100px distance threshold prevents tracker "teleportation" due to background color matches.
- **Minimum Movement Threshold** (7px): Prevents ghost lines when pen is stationary.
- **Largest Blob Tracking**: Only tracks the single largest valid contour (area > 1500px), ignoring smaller false positives.

### 🔄 Automatic Color Calibration Sync
- **Created** `pen_config.json` as a shared configuration file between `picker.py` and `drawing.py`.
- `picker.py` saves HSV values with **'s'** key; `drawing.py` loads them automatically on startup.
- Added **calibration warnings** if HSV range is too broad (Hue range > 60 or Sat Min < 50).

### ✏️ Toggle-Based "Pen Lift" (Hover Mode)
- **Spacebar Toggle**: Press once to switch between Writing and Hovering modes.
- **Auto line-break**: Switching from Hover to Writing automatically resets `prevPoints` to prevent "connector lines".
- **Visual indicators**: `[ MODE: WRITING ]` (Green) / `[ MODE: HOVERING ]` (Red) displayed on screen.
- **Cursor styles**: Solid Red Dot (Writing) / Hollow Yellow Ring (Hovering).

### ↩️ Multi-Step Undo System
- Stores up to **10 canvas snapshots** in an undo buffer.
- Snapshots are taken when a stroke ends (pen disappears from frame).
- Press **'z'** to undo the last stroke.

### 🖌️ Dynamic Brush Controls
- **Up/Down Arrow keys** (or 'w'/'s') change brush thickness in real-time (range: 2px – 50px).
- Current brush size displayed in the UI overlay.

### 📊 Real-Time UI Overlay
- **FPS Counter**: Frames per second displayed live.
- **Brush Size**: Current thickness indicator.
- **History Count**: Number of available undo steps.
- **Mode Status**: Current drawing/hovering state with color-coded text.

### 📷 Continuity Camera Support
- Full support for **iPhone as webcam** via macOS Continuity Camera.
- `CAMERA_INDEX` configuration variable for easy switching between cameras.
- `test_cameras.py` utility for discovering and visually identifying available cameras.

### 🛠️ Utility Scripts
- **`picker.py`**: HSV color tuning utility with save/load functionality.
- **`test_cameras.py`**: Visual camera identification and selection tool.

---

## Project Files

| File | Purpose |
|---|---|
| `drawing.py` | Main application (MediaPipe hand tracking + canvas rendering) |
| `euro_filter.py` | 1 Euro Filter implementation for adaptive smoothing |
| `hand_landmarker.task` | MediaPipe hand landmark detection model (float16) |
| `picker.py` | HSV color calibration utility (Phase 1, deprecated) |
| `pen_config.json` | Saved HSV calibration values (Phase 1, deprecated) |
| `test_cameras.py` | Visual camera identification tool |
| `synopsis.md` | Academic project synopsis with flowchart |
| `README.md` | Project documentation and setup guide |
