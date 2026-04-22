# MajorProject: Pro Suite Air Canvas

A real-time, interactive drawing application powered by **OpenCV** and **Python**. Move a colored object (like a pen cap) in front of your camera to draw in thin air on a digital canvas.

## 🚀 Key Features

*   **Continuous Smooth Strokes**: Uses point-to-point line interpolation to eliminate dotted lines and ensure fluid drawing.
*   **Kalman Filter Smoothing**: Advanced mathematical filtering to predict path movement and remove hand jitters/camera noise.
*   **Multi-Step Undo**: Intelligent stroke-based history allowing you to step back your last 10 actions.
*   **Apple Continuity Camera Support**: Seamlessly use your iPhone as a high-quality wireless webcam.
*   **Dynamic Controls**: Change brush thickness and clear the canvas in real-time via keyboard shortcuts.
*   **Performance Monitoring**: Built-in FPS and status overlay.

## 🛠 Project Setup

This project uses [uv](https://github.com/astral-sh/uv), a blazing-fast Python package manager.

```bash
# Initialize dependencies
uv add opencv-python numpy
```

## 🎮 How to Use

### 1. Identify Your Camera
If you are using an external camera or Continuity Camera, run the test utility to find the correct index:
```bash
uv run test_cameras.py
```
Update `CAMERA_INDEX` at the top of `drawing.py` if necessary.

### 2. Tune Your Tracking Color
Because lighting varies, use the color picker to isolate your tracking object:
```bash
uv run picker.py
```
*Adjust the sliders until only your object is white. Press **'s'** to save the values automatically for `drawing.py`.*

### 3. Start Drawing
```bash
uv run drawing.py
```

## ⌨️ Controls

| Key | Action |
| --- | --- |
| **z** | Undo last stroke |
| **c** | Clear entire canvas |
| **Up Arrow** / **w** | Increase Brush Size |
| **Down Arrow** / **s** | Decrease Brush Size |
| **q** | Quit Application |

## 📂 Project Structure

*   `drawing.py`: The main "Pro Suite" application.
*   `picker.py`: HSV tuning utility for color tracking.
*   `test_cameras.py`: Utility to list available camera devices.
*   `main.py`: Entry point for the project.

---

*Built with ❤️ using OpenCV on macOS.*
