# Ink-in-Air Gesture Drawing System: Advanced AI-Powered Spatial Art Suite

Ink-in-Air Gesture Drawing System is a professional-grade, real-time interactive drawing application that allows users to create digital art in 3D space using natural hand gestures. By leveraging state-of-the-art Computer Vision and Deep Learning, the system transforms your webcam into a boundless digital canvas.

## 🚀 Key Features

### 👐 Dual-Hand Interaction Model
Experience a natural workstation workflow by separating creative and technical tasks:
- **Right Hand (The Artist)**: Point with only your index finger (pinky folded) to **Draw/Erase**. Extend both your index and pinky fingers (like the "rock on" sign) to **Hover** (move the cursor without drawing).
- **Left Hand (The Controller)**: Manage your digital studio. Use your left hand to switch colors, adjust brush sizes, lock/unlock thickness, and trigger system actions without interrupting your right hand's creative flow.

### 🎨 Premium Virtual UI (Glassmorphism)
- **Modern HUD**: A sleek, semi-transparent heads-up display featuring rounded pill-shaped buttons.
- **Visual Feedback**: Active tools and selected colors feature a "glow" highlight for instant orientation.
- **Real-time Status**: Floating status indicators track your hand to show current modes (DRAWING, HOVERING, ERASING).

### 📐 Multi-Shape & Polygon Snapping
The AI understands your intent. Draw a rough approximation of a shape, and the system snaps it to clean geometry:
- **Straight Lines**: Snaps any straight-ish line drawn between two points into a perfect straight line.
- **Circles & Ellipses (Ovals)**: Snaps circular curves, or elongated shapes into mathematically fitted ellipses.
- **Rotated Rectangles**: Snaps rectangles at any angle using rotated bounding boxes (`cv2.minAreaRect`).
- **Triangles, Pentagons, Hexagons**: Snaps 3, 5, and 6-sided polygons cleanly.
- **Convex Hull Smoothing**: Smoothes out tremors and automatically closes shapes that you don't close perfectly in the air.
- **Handwriting Protection Guards**: Rejects small strokes (`hull_area < 350`) or short straight-line corrections (`line_dist < 50px`). Crucially, an **Open Contour Guard** detects gaps between the start and end of a stroke; if the gap is larger than 22% of the perimeter (which is true for open letters like C, S, V, W, U, M, N), shape snapping is blocked, ensuring normal handwriting remains untouched.
- **Zero-Overlap Snapping**: Wipes out the rough hand-drawn trajectory when a shape is successfully detected, drawing only the clean shape on the canvas (no double/overlapping ink).

### 🔒 Left-Hand Pinky Size Lock
- **Adjusting Mode (Pinky Extended)**: Keep your left middle and ring fingers folded, and extend your pinky finger. Pinch/spread your thumb and index to adjust brush size (HUD turns **cyan**).
- **Locked Mode (Pinky Folded)**: Fold your left pinky finger (along with middle and ring fingers). The sizing locks at the current value (HUD turns **green** and displays `LOCKED`).

### 🧠 Advanced Tracking & Smoothing
- **MediaPipe Tasks API**: High-fidelity 21-point hand landmark tracking.
- **Tuned 1 Euro Filter**: Adaptive smoothing (`min_cutoff=0.6`, `beta=0.05`) designed to eliminate tremors while maintaining ultra-low latency for writing and drawing.
- **Continuous Fast Strokes**: An increased distance connection threshold (`d < 400`) prevents lines from breaking during rapid writing or drawing movements.
- **Sub-Pixel Anti-Aliasing**: Smooth, professional-grade strokes (LINE_AA).
- **Spatial Handedness Filter**: Restricts settings adjustments to the left half of the screen (default settings side). If the drawing hand crosses the center line and is misclassified as the Left hand, the system automatically corrects its type to `Right` (drawing hand) on-the-fly, preventing accidental brush size changes.

---

## 🛠 Project Setup

This project uses the `uv` package manager for high-performance dependency management.

```bash
# Install dependencies
uv add opencv-python mediapipe numpy

# Run the application
uv run drawing.py
```

### Hand Tracking Model
Ensure `hand_landmarker.task` is present in the root directory. This is the pre-trained model required for the MediaPipe Tasks API (download it from the [Google MediaPipe Tasks Model Repository](https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task)).

---

## 🎮 Controls and Gestures

### Hand Roles
| Hand | Role | Primary Actions |
| --- | --- | --- |
| **Right Hand** | Artist | Drawing (Index up, Pinky folded), Hovering (Index + Pinky up), Shape Creation |
| **Left Hand** | Controller | Palette selection, Brush sizing (Thumb-Index dist), Pinky Lock, Invert Toggle |

### Left-Hand Brush Sizing & Lock
* **Adjust (Pinky Extended)**: Middle + Ring folded, Pinky extended.
* **Lock (Pinky Folded)**: Middle + Ring folded, Pinky folded.

### Virtual Tool Palette (Top Bar)
- **Colors**: RED, GREEN, BLUE, YELLOW.
- **ERASER**: 2x thick brush to clear the canvas.
- **SAVE**: Capture your artwork to the `screenshots/` folder.
- **INVERT**: Instantly swap the roles of your Left and Right hands (useful for left-handed artists).

### Keyboard Shortcuts
| Key | Action |
| --- | --- |
| **z** | Undo last stroke/shape |
| **c** | Clear entire canvas |
| **s** | Save drawing |
| **q** | Quit application |

---

## 📂 Project Structure

- `drawing.py`: The heart of the application. Handles dual-hand logic, UI rendering, and gesture processing.
- `euro_filter.py`: Implementation of the adaptive 1 Euro Filter for jitter-free tracking.
- `test_cameras.py`: Utility to identify and preview available camera indices.
- `hand_landmarker.task`: The deep learning model for hand tracking.
- `screenshots/`: Automatically generated folder for your saved artwork.

---

## 🛠 Technical Credits
Built with ❤️ using:
- **OpenCV**: Image processing and UI rendering.
- **MediaPipe**: Hand landmark detection and tracking.
- **NumPy**: Mathematical operations and point processing.
- **Python**: Core application logic.
