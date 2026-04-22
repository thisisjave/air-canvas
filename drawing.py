"""
Air Canvas Pro Suite — Phase 2: MediaPipe Hand Tracking
=======================================================
Tracks your index finger using AI-powered hand landmark detection.
No calibration, no pen, no environment dependency.

Gesture Controls:
  - 1 Finger Up (Index)            → DRAWING mode
  - 2 Fingers Up (Index + Middle)  → HOVERING mode (move without drawing)

Keyboard Controls:
  - 'z'       → Undo last stroke
  - 'c'       → Clear canvas
  - 'q'       → Quit
  - Up/Down   → Increase/Decrease brush size
  - 'w'/'s'   → Increase/Decrease brush size (fallback)
"""

import cv2
import numpy as np
import time
import mediapipe as mp
from euro_filter import OneEuroFilter

# --- Configuration ---
CAMERA_INDEX = 0  # 0 = iPhone (1920x1080) | 1 = MacBook (1280x720)
MODEL_PATH = "hand_landmarker.task"

cap = cv2.VideoCapture(CAMERA_INDEX)

# Drawing Ink Color (BGR format)
DRAW_COLOR = (0, 0, 255)  # Red ink

# --- MediaPipe Tasks API Setup ---
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=VisionRunningMode.VIDEO,
    num_hands=1,
    min_hand_detection_confidence=0.7,
    min_hand_presence_confidence=0.7,
    min_tracking_confidence=0.7
)

landmarker = HandLandmarker.create_from_options(options)

# --- 1 Euro Filter Setup (replaces Kalman + EMA) ---
filter_x = OneEuroFilter(freq=30.0, min_cutoff=0.3, beta=0.02, d_cutoff=1.0)
filter_y = OneEuroFilter(freq=30.0, min_cutoff=0.3, beta=0.02, d_cutoff=1.0)

# --- Drawing State ---
brush_thickness = 10
undo_list = []
max_undos = 10
stroke_active = False
prevPoint = None
prev_time = 0
imgCanvas = None
frame_count = 0

# Gesture state
writing_active = False  # Start in hover mode
gesture_text = "HOVERING"


def count_fingers_up(hand_landmarks, img_w, img_h):
    """
    Determine which fingers are extended (up).
    Returns a list of booleans: [thumb, index, middle, ring, pinky]
    
    Uses MediaPipe Tasks API landmark format (NormalizedLandmark objects).
    """
    tips = [4, 8, 12, 16, 20]   # Fingertip landmark IDs
    pips = [3, 6, 10, 14, 18]   # PIP/IP joint landmark IDs
    
    fingers = []
    
    # Thumb: compare X position (works for right hand facing camera after flip)
    thumb_tip_x = hand_landmarks[tips[0]].x
    thumb_ip_x = hand_landmarks[pips[0]].x
    fingers.append(thumb_tip_x < thumb_ip_x)  # After mirror flip
    
    # Other 4 fingers: tip above PIP = finger is up
    for i in range(1, 5):
        tip_y = hand_landmarks[tips[i]].y
        pip_y = hand_landmarks[pips[i]].y
        fingers.append(tip_y < pip_y)
    
    return fingers


def draw_hand_landmarks(img, landmarks, iw, ih):
    """Draw hand skeleton connections on the image."""
    # MediaPipe hand connections
    connections = [
        (0,1),(1,2),(2,3),(3,4),      # Thumb
        (0,5),(5,6),(6,7),(7,8),      # Index
        (5,9),(9,10),(10,11),(11,12), # Middle
        (9,13),(13,14),(14,15),(15,16), # Ring
        (13,17),(17,18),(18,19),(19,20), # Pinky
        (0,17)                         # Palm base
    ]
    
    points = []
    for lm in landmarks:
        px, py = int(lm.x * iw), int(lm.y * ih)
        points.append((px, py))
        cv2.circle(img, (px, py), 4, (0, 255, 0), cv2.FILLED)
    
    for start, end in connections:
        cv2.line(img, points[start], points[end], (0, 255, 0), 2)


print(f"Starting Camera {CAMERA_INDEX}...")
print("Phase 2: MediaPipe Hand Tracking Active")
print("Gestures: 1 Finger=Draw, 2 Fingers=Hover")
print("Keys: 'z'=Undo, 'c'=Clear, 'q'=Quit, Up/Down=Brush Size")

while True:
    success, img = cap.read()
    if not success:
        break
    
    img = cv2.flip(img, 1)
    imgResult = img.copy()
    ih, iw, _ = img.shape
    
    if imgCanvas is None:
        imgCanvas = np.zeros_like(img)
        undo_list.append(imgCanvas.copy())
    
    # FPS calculation
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time) if prev_time != 0 else 0
    prev_time = curr_time
    
    # --- MediaPipe Hand Detection (Tasks API) ---
    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=imgRGB)
    
    # Use incrementing timestamp for VIDEO mode
    frame_count += 1
    timestamp_ms = int(frame_count * (1000 / 30))  # Approximate 30 FPS timestamps
    
    result = landmarker.detect_for_video(mp_image, timestamp_ms)
    
    hand_detected = False
    
    if result.hand_landmarks:
        for hand_lms in result.hand_landmarks:
            hand_detected = True
            
            # Draw hand skeleton on live feed
            draw_hand_landmarks(imgResult, hand_lms, iw, ih)
            
            # Get Index Finger Tip (Landmark 8)
            raw_x = int(hand_lms[8].x * iw)
            raw_y = int(hand_lms[8].y * ih)
            
            # Apply 1 Euro Filter for smooth tracking
            t = time.time()
            cx = int(filter_x.filter(raw_x, t))
            cy = int(filter_y.filter(raw_y, t))
            
            # --- Gesture Detection ---
            fingers = count_fingers_up(hand_lms, iw, ih)
            index_up = fingers[1]
            middle_up = fingers[2]
            
            # Gesture Logic:
            # 1 finger (index only) = DRAWING
            # 2 fingers (index + middle) = HOVERING
            if index_up and not middle_up:
                # DRAWING MODE
                if not writing_active:
                    # Just switched to drawing — reset filter and previous point
                    prevPoint = None
                    filter_x.reset()
                    filter_y.reset()
                    cx = int(filter_x.filter(raw_x, time.time()))
                    cy = int(filter_y.filter(raw_y, time.time()))
                writing_active = True
                gesture_text = "DRAWING"
                
                # Show solid drawing cursor
                cv2.circle(imgResult, (cx, cy), 15, DRAW_COLOR, cv2.FILLED)
                
                # Mark stroke as active for undo system
                stroke_active = True
                
                if prevPoint is not None:
                    dist = np.linalg.norm(np.array([cx, cy]) - np.array(prevPoint))
                    if 2 < dist < 100:
                        cv2.line(imgCanvas, (prevPoint[0], prevPoint[1]), (cx, cy), DRAW_COLOR, brush_thickness, cv2.LINE_AA)
                prevPoint = [cx, cy]
                
            elif index_up and middle_up:
                # HOVERING MODE
                if writing_active and stroke_active:
                    # Stroke just ended — take undo snapshot
                    undo_list.append(imgCanvas.copy())
                    if len(undo_list) > max_undos + 1:
                        undo_list.pop(0)
                    stroke_active = False
                
                writing_active = False
                gesture_text = "HOVERING"
                prevPoint = None
                
                # Show hover cursor (hollow yellow ring)
                cv2.circle(imgResult, (cx, cy), 15, (255, 255, 0), 2)
            
            else:
                # Other gestures — keep current state, show appropriate cursor
                if writing_active:
                    cv2.circle(imgResult, (cx, cy), 15, DRAW_COLOR, cv2.FILLED)
                else:
                    cv2.circle(imgResult, (cx, cy), 15, (255, 255, 0), 2)
    
    if not hand_detected:
        # Hand left the frame — end stroke if active
        if stroke_active:
            undo_list.append(imgCanvas.copy())
            if len(undo_list) > max_undos + 1:
                undo_list.pop(0)
            stroke_active = False
        prevPoint = None
        filter_x.reset()
        filter_y.reset()
    
    # --- UI Overlay ---
    cv2.putText(imgResult, f'FPS: {int(fps)}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    cv2.putText(imgResult, f'Brush Size: {brush_thickness}', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    cv2.putText(imgResult, f'History: {len(undo_list)-1}', (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    
    # Mode Status Indicator
    mode_color = (0, 255, 0) if writing_active else (0, 0, 255)
    cv2.putText(imgResult, f'[ {gesture_text} ]', (iw - 220, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, mode_color, 2)
    
    # --- Merge Canvas ---
    imgGray = cv2.cvtColor(imgCanvas, cv2.COLOR_BGR2GRAY)
    _, imgInv = cv2.threshold(imgGray, 1, 255, cv2.THRESH_BINARY_INV)
    imgInv = cv2.cvtColor(imgInv, cv2.COLOR_GRAY2BGR)
    imgResult = cv2.bitwise_and(imgResult, imgInv)
    imgResult = cv2.bitwise_or(imgResult, imgCanvas)
    
    cv2.imshow("Air Canvas - Phase 2", imgResult)
    
    # --- Keyboard Controls ---
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('c'):
        imgCanvas = np.zeros_like(img)
        undo_list = [imgCanvas.copy()]
        prevPoint = None
    elif key == ord('z'):
        if len(undo_list) > 1:
            undo_list.pop()
            imgCanvas = undo_list[-1].copy()
            prevPoint = None
    elif key == 0 or key == 82:  # Up Arrow
        brush_thickness = min(brush_thickness + 2, 50)
    elif key == 1 or key == 84:  # Down Arrow
        brush_thickness = max(brush_thickness - 2, 2)
    elif key == ord('w'):
        brush_thickness = min(brush_thickness + 2, 50)
    elif key == ord('s'):
        brush_thickness = max(brush_thickness - 2, 2)

landmarker.close()
cap.release()
cv2.destroyAllWindows()