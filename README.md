# Air Canvas Pro: Advanced AI-Powered Spatial Art Suite

Air Canvas Pro is a professional-grade, real-time interactive drawing application that allows users to create digital art in 3D space using natural hand gestures. By leveraging state-of-the-art Computer Vision and Deep Learning, the system transforms your webcam into a boundless digital canvas.

## 🚀 Key Features

### 👐 Dual-Hand Interaction Model
Experience a natural workstation workflow by separating creative and technical tasks:
- **Right Hand (The Artist)**: Dedicated to high-precision drawing, hovering, and shape creation.
- **Left Hand (The Controller)**: Manage your digital studio. Use your left hand to switch colors, adjust brush sizes, and trigger system actions without interrupting your right hand's creative flow.

### 🎨 Premium Virtual UI (Glassmorphism)
- **Modern HUD**: A sleek, semi-transparent heads-up display featuring rounded pill-shaped buttons.
- **Visual Feedback**: Active tools and selected colors feature a "glow" highlight for instant orientation.
- **Real-time Status**: Floating status indicators track your hand to show current modes (DRAWING, HOVERING, ERASING).

### 📐 Intelligent Shape Recognition
The AI understands your intent. Draw a rough approximation of a **Circle**, **Rectangle**, or **Triangle**, and the system will automatically "snap" it to a perfect geometric shape when you lift your finger.

### 📏 Dynamic Gesture-Based Sizing
Adjust your brush thickness in real-time using natural spacing. Simply spread your **left thumb and index finger** apart to increase size, or bring them together to shrink it.

### 🧠 Advanced Tracking & Smoothing
- **MediaPipe Tasks API**: High-fidelity 21-point hand landmark tracking.
- **1 Euro Filter**: Industry-standard adaptive smoothing that eliminates tremors while maintaining zero latency for fast movements.
- **Sub-Pixel Anti-Aliasing**: Smooth, professional-grade strokes (LINE_AA).

---

## 🛠 Project Setup

This project uses the `uv` package manager for high-performance dependency management.

```bash
# Clone the repository and install dependencies
uv add opencv-python mediapipe numpy
```

### Hand Tracking Model
Ensure `hand_landmarker.task` is present in the root directory. This is the pre-trained model required for the MediaPipe Tasks API.

---

## 🎮 Controls and Gestures

### Hand Roles
| Hand | Role | Primary Actions |
| --- | --- | --- |
| **Right Hand** | Artist | Drawing (1 finger), Hovering (2 fingers), Shape Creation |
| **Left Hand** | Controller | Palette selection, Brush sizing (Thumb-Index dist), Invert Toggle |

### Virtual Tool Palette (Top Bar)
- **Colors**: RED, GREEN, BLUE, YELLOW.
- **ERASER**: 2x thick brush to clear the canvas.
- **SAVE**: Capture your artwork to the `screenshots/` folder.
- **INVERT**: Instantly swap the roles of your Left and Right hands.

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
