# GestureDraw: Advanced AI-Powered Air Canvas

GestureDraw is a real-time, interactive drawing application that allows users to create digital art in 3D space using natural hand gestures. By leveraging Computer Vision and Deep Learning, the system tracks hand movements through a standard webcam and translates them into smooth, digital strokes.

## Key Features

*   **MediaPipe Hand Tracking**: Utilizes Google's Hand Landmark detection to track 21 distinct 3D points on the hand, providing high-fidelity tracking without the need for physical colored markers.
*   **Gesture-Based Control**: Implements a natural user interface where specific finger orientations toggle between drawing and hovering modes, eliminating the need for constant keyboard interaction.
*   **1 Euro Filter Smoothing**: Employs an industry-standard adaptive low-pass filter that dynamically adjusts smoothing based on movement speed. This eliminates hand tremors during slow drawing while maintaining responsiveness during fast strokes.
*   **Anti-Aliased Rendering**: High-quality stroke rendering using sub-pixel anti-aliasing (LINE_AA) for professional-grade visual output.
*   **Multi-Step Undo System**: Intelligent stroke-based history management allowing users to revert their last 10 actions.
*   **Apple Continuity Camera Support**: Optimized for high-resolution input using iPhone as a wireless webcam on macOS.
*   **Visual Performance Overlay**: Integrated heads-up display (HUD) showing real-time FPS, brush size, and system status.

## Project Setup

This project utilizes the uv package manager for dependency isolation and performance.

```bash
# Install dependencies
uv add opencv-python mediapipe numpy
```

## How to Use

### 1. Camera Configuration
Run the camera identification utility to select your preferred input device (e.g., MacBook FaceTime camera or iPhone):
```bash
uv run test_cameras.py
```
Update the `CAMERA_INDEX` constant in `drawing.py` if your preferred device is not the default (Index 0).

### 2. Execution
Launch the main application:
```bash
uv run drawing.py
```

## Controls and Gestures

### Hand Gestures
| Gesture | Action |
| --- | --- |
| 1 Finger Up (Index) | Drawing Mode: Strokes follow the fingertip |
| 2 Fingers Up (Index + Middle) | Hovering Mode: Move the cursor without drawing |

### Keyboard Shortcuts
| Key | Action |
| --- | --- |
| z | Undo last stroke |
| c | Clear entire canvas |
| Up Arrow / w | Increase brush size |
| Down Arrow / s | Decrease brush size |
| q | Quit application |

## Project Structure

*   `drawing.py`: Main application core integrating MediaPipe tracking and canvas rendering.
*   `euro_filter.py`: Implementation of the 1 Euro Filter algorithm for adaptive smoothing.
*   `hand_landmarker.task`: Pre-trained deep learning model for hand landmark detection.
*   `test_cameras.py`: Utility for identifying and previewing available camera devices.
*   `synopsis.md`: Academic project documentation including flowcharts.
*   `CHANGELOG.md`: Detailed history of project upgrades and technical milestones.

## Technical Credits
Built using OpenCV, MediaPipe, and NumPy.
Developed as a project for [Your Institution/Purpose].
