"""
Ink-in-Air Gesture Drawing System — Phase 2: MediaPipe Hand Tracking
====================================================================
Tracks your index finger using AI-powered hand landmark detection.
No calibration, no pen, no environment dependency.

Gesture Controls:
  - Index Finger Only (Pinky Folded)  → DRAWING mode
  - Index + Pinky Fingers Extended    → HOVERING mode (move without drawing)

Keyboard Controls:
  - 'z'       → Undo last stroke
  - 'x'       → Redo last undone stroke
  - 'c'       → Clear canvas (with swipe right restore backup)
  - 'q'       → Quit
  - Up/Down   → Increase/Decrease brush size
  - 'w'/'s'   → Increase/Decrease brush size (fallback)
"""

import cv2
import numpy as np
import time
import os
import datetime
import mediapipe as mp
from euro_filter import OneEuroFilter
from hud_renderer import (
    draw_toolbar,
    draw_floating_status,
    draw_stats_overlay,
    draw_glass_rect,
    GLASS_BG,
)

# --- Configuration ---
CAMERA_INDEX = 0  # 0 = iPhone (1920x1080) | 1 = MacBook (1280x720)
MODEL_PATH = "hand_landmarker.task"
SWAP_HANDS = True  # Set to True if your Left/Right hands are swapped

cap = cv2.VideoCapture(CAMERA_INDEX)

# Drawing Ink Colors (BGR format)
COLORS = [
    (0, 0, 255),    # Red
    (0, 255, 0),    # Green
    (255, 0, 0),    # Blue
    (0, 255, 255),  # Yellow
    (255, 255, 255) # White
]
DRAW_COLOR = COLORS[0]  # Start with Red
ERASER_MODE = False

# --- MediaPipe Tasks API Setup ---
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=VisionRunningMode.VIDEO,
    num_hands=2,
    min_hand_detection_confidence=0.7,
    min_hand_presence_confidence=0.7,
    min_tracking_confidence=0.7
)

landmarker = HandLandmarker.create_from_options(options)

# --- 1 Euro Filter Setup (replaces Kalman + EMA) ---
filter_x = OneEuroFilter(freq=30.0, min_cutoff=0.6, beta=0.05, d_cutoff=1.0)
filter_y = OneEuroFilter(freq=30.0, min_cutoff=0.6, beta=0.05, d_cutoff=1.0)

# --- Drawing State ---
brush_thickness = 10
undo_list = []
redo_list = []
max_undos = 20
stroke_active = False
current_stroke = []  # List of (x, y) points for the active stroke
prevPoint = None
prev_time = 0
imgCanvas = None
imgCanvasPrev = None
frame_count = 0
left_hand_history = []
last_swipe_time = 0
swipe_cooldown = 1.0
toast_message = None
toast_timer = 0
pre_clear_canvas = None
pre_clear_undo_list = None

# --- Virtual Palette Setup ---
header_height = 100
# Cooldown for toggle actions (Save, Invert)
last_action_time = 0
cooldown_duration = 1.0 # seconds

# Gesture state
writing_active = False  # Start in hover mode
gesture_text = "HOVERING"

# HUD state — fingertip position for floating status pill
right_fingertip: tuple | None = None

TOOL_NAMES  = ["RED", "GREEN", "BLUE", "YELLOW", "ERASER", "SAVE", "INVERT"]
TOOL_COLORS = [(0,0,255),(0,255,0),(255,0,0),(0,255,255),(200,200,200),(100,100,100),(255,0,255)]
hover_tool_idx = -1  # which palette button the left hand is hovering over


def count_fingers_up(hand_landmarks, img_w, img_h, hand_type="Right"):
    """
    Determine which fingers are extended (up).
    Returns a list of booleans: [thumb, index, middle, ring, pinky]
    
    Uses MediaPipe Tasks API landmark format (NormalizedLandmark objects).
    """
    tips = [4, 8, 12, 16, 20]   # Fingertip landmark IDs
    pips = [3, 6, 10, 14, 18]   # PIP/IP joint landmark IDs
    
    fingers = []
    
    # Thumb: compare X position (account for Left vs Right hand and flip)
    thumb_tip_x = hand_landmarks[tips[0]].x
    thumb_ip_x = hand_landmarks[pips[0]].x
    if hand_type == "Right":
        fingers.append(thumb_tip_x < thumb_ip_x)
    else:
        fingers.append(thumb_tip_x > thumb_ip_x)
    
    # Other 4 fingers: tip above PIP = finger is up
    for i in range(1, 5):
        tip_y = hand_landmarks[tips[i]].y
        pip_y = hand_landmarks[pips[i]].y
        fingers.append(tip_y < pip_y)
    
    # Calculate distance between thumb and index unconditionally
    tx, ty = hand_landmarks[4].x * img_w, hand_landmarks[4].y * img_h
    ix, iy = hand_landmarks[8].x * img_w, hand_landmarks[8].y * img_h
    dist = np.sqrt((tx - ix)**2 + (ty - iy)**2)

    return fingers, dist


def save_drawing(img):
    """Save the current frame to the screenshots directory."""
    global toast_message, toast_timer
    if not os.path.exists("screenshots"):
        os.makedirs("screenshots")
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshots/canvas_{timestamp}.png"
    cv2.imwrite(filename, img)
    print(f"Saved: {filename}")
    toast_message = "CANVAS SAVED!"
    toast_timer = time.time()


def recognize_shape(points):
    """
    Analyze a list of points to see if it approximates a circle, rectangle, triangle, ellipse, pentagon, hexagon, or line.
    Returns (shape_type, params) or (None, None).
    """
    if len(points) < 8:  # Lowered limit to support fast drawings
        return None, None
    
    # Convert points to numpy array
    pts = np.array(points, dtype=np.int32)
    
    # --- 1. Straight Line Check ---
    start_pt = pts[0]
    end_pt = pts[-1]
    line_dist = np.linalg.norm(start_pt - end_pt)
    
    # Compute total path length
    diffs = np.diff(pts, axis=0)
    total_dist = np.sum(np.sqrt(np.sum(diffs**2, axis=1)))
    
    # Only snap to LINE if it's long enough (> 50px) and straight
    if total_dist > 0 and (line_dist / total_dist) > 0.90 and line_dist > 50:
        return "LINE", (tuple(start_pt), tuple(end_pt))

    # --- 2. Convex Hull & Preprocessing ---
    hull = cv2.convexHull(pts)
    hull_area = cv2.contourArea(hull)
    hull_peri = cv2.arcLength(hull, True)
    
    # Reject shape snapping for small writing, dots, or details (hull_area < 350)
    if hull_peri == 0 or hull_area < 350:
        return None, None
        
    # --- 3. Closed Shape Guard ---
    # For any closed shape (Circle, Rect, Ellipse, Polygons), the start and end of the stroke
    # must be relatively close to form a closed loop. This prevents open letters (C, S, U, V, etc.) from snapping.
    start_end_dist = np.linalg.norm(start_pt - end_pt)
    if start_end_dist > 0.22 * hull_peri:
        return None, None

    # Get rotated bounding rectangle (rotation-invariant)
    rot_rect = cv2.minAreaRect(hull)
    box_points = np.int32(cv2.boxPoints(rot_rect))
    rw, rh = rot_rect[1]
    rect_area = rw * rh
    
    # Get minimum enclosing circle
    (cx, cy), radius = cv2.minEnclosingCircle(hull)
    circle_area = np.pi * (radius ** 2)
    
    # Compute shape descriptors on the Convex Hull
    circularity = 4 * np.pi * hull_area / (hull_peri ** 2)
    rect_fill_ratio = hull_area / rect_area if rect_area > 0 else 0
    circle_fill_ratio = hull_area / circle_area if circle_area > 0 else 0
    
    # --- 4. Circle Check ---
    if circularity > 0.82 and circle_fill_ratio > 0.70:
        return "CIRCLE", (int(cx), int(cy), int(radius))
        
    # --- 5. Rectangle Check ---
    if rect_fill_ratio > 0.80:
        return "RECTANGLE", box_points
        
    # --- 6. Ellipse / Oval Check ---
    if len(pts) >= 5:
        ellipse_box = cv2.fitEllipse(pts)
        _, (ew, eh), _ = ellipse_box
        ellipse_area = np.pi * (ew / 2) * (eh / 2)
        ellipse_fill_ratio = hull_area / ellipse_area if ellipse_area > 0 else 0
        
        if ellipse_fill_ratio > 0.85 and circularity > 0.40:
            return "ELLIPSE", ellipse_box
            
    # --- 7. Polygon Checks (Triangle, Pentagon, Hexagon) ---
    approx = cv2.approxPolyDP(hull, 0.045 * hull_peri, True)
    num_verts = len(approx)
    
    if num_verts == 3:
        return "TRIANGLE", approx
    elif num_verts == 5:
        return "PENTAGON", approx
    elif num_verts == 6:
        return "HEXAGON", approx
        
    # Try alternative epsilons to see if we can cleanly resolve vertices
    for eps_factor in [0.03, 0.05, 0.07, 0.09]:
        approx_alt = cv2.approxPolyDP(hull, eps_factor * hull_peri, True)
        n_verts_alt = len(approx_alt)
        if n_verts_alt == 3:
            return "TRIANGLE", approx_alt
        elif n_verts_alt == 4:
            if rect_fill_ratio > 0.65:
                return "RECTANGLE", box_points
        elif n_verts_alt == 5:
            return "PENTAGON", approx_alt
        elif n_verts_alt == 6:
            return "HEXAGON", approx_alt

    # Fallback/Borderline Case: 4 approximated vertices but low fill ratio is likely a triangle
    if num_verts == 4 and rect_fill_ratio < 0.65:
        approx_3 = cv2.approxPolyDP(hull, 0.08 * hull_peri, True)
        if len(approx_3) == 3:
            return "TRIANGLE", approx_3
            
    return None, None


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
print("Keys: 'z'=Undo, 'x'=Redo, 'c'=Clear, 'q'=Quit, Up/Down=Brush Size")

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
        hand_detected = True
        
    # --- Antigravity HUD: Toolbar ---
    hud_state = {
        "header_height": header_height,
        "tool_names":    TOOL_NAMES,
        "tool_colors":   TOOL_COLORS,
        "colors":        COLORS,
        "draw_color":    DRAW_COLOR,
        "eraser_mode":   ERASER_MODE,
        "swap_hands":    SWAP_HANDS,
        "hover_tool_idx": hover_tool_idx,
    }
    draw_toolbar(imgResult, hud_state, frame_count)

    right_hand_this_frame = False
    right_fingertip = None
    hover_tool_idx = -1  # reset each frame; updated in Left hand block
    
    if hand_detected:
        # Iterate through all detected hands
        for idx, hand_lms in enumerate(result.hand_landmarks):
            # Get handedness (Left vs Right)
            hand_type = result.handedness[idx][0].category_name 
            
            # Swap logic if configuration is enabled
            if SWAP_HANDS:
                hand_type = "Right" if hand_type == "Left" else "Left"
                
            # --- Spatial Hand Type Correction Filter ---
            # Corrects handedness misclassifications based on screen position
            wrist_x = hand_lms[0].x * iw
            settings_on_left = True
            if hand_type == "Left":
                if (settings_on_left and wrist_x > iw * 0.5) or (not settings_on_left and wrist_x < iw * 0.5):
                    hand_type = "Right"
            
            # Draw hand skeleton on live feed
            draw_hand_landmarks(imgResult, hand_lms, iw, ih)
            
            # --- Hand-Specific Logic ---
            if hand_type == "Right":  # RIGHT HAND = DRAWING
                right_hand_this_frame = True
                # Get Index Finger Tip (Landmark 8)
                raw_x = int(hand_lms[8].x * iw)
                raw_y = int(hand_lms[8].y * ih)
                
                # Apply 1 Euro Filter for smooth tracking
                t = time.time()
                cx = int(filter_x.filter(raw_x, t))
                cy = int(filter_y.filter(raw_y, t))
                right_fingertip = (cx, cy)  # for floating status pill
                
                # --- Gesture Detection ---
                fingers, _ = count_fingers_up(hand_lms, iw, ih, hand_type)
                index_up = fingers[1]
                pinky_up = fingers[4]
                
                # Right hand only handles drawing/hovering
                if index_up and not pinky_up:
                    # DRAWING MODE
                    if not writing_active:
                        prevPoint = None
                        filter_x.reset()
                        filter_y.reset()
                        cx = int(filter_x.filter(raw_x, time.time()))
                        cy = int(filter_y.filter(raw_y, time.time()))
                        current_stroke = []
                        imgCanvasPrev = imgCanvas.copy()
                    
                    writing_active = True
                    gesture_text = "ERASING" if ERASER_MODE else "DRAWING"
                    
                    # Eraser is 2x larger for better usability
                    current_thickness = brush_thickness * 2 if ERASER_MODE else brush_thickness
                    
                    cursor_color = (255, 255, 255) if ERASER_MODE else DRAW_COLOR
                    cv2.circle(imgResult, (cx, cy), current_thickness + 5, cursor_color, cv2.FILLED)
                    cv2.circle(imgResult, (cx, cy), current_thickness + 7, (0, 0, 0), 2)
                    
                    stroke_active = True
                    
                    if prevPoint is not None:
                        d = np.linalg.norm(np.array([cx, cy]) - np.array(prevPoint))
                        if 2 < d < 400:
                            draw_color = (0, 0, 0) if ERASER_MODE else DRAW_COLOR
                            cv2.line(imgCanvas, (prevPoint[0], prevPoint[1]), (cx, cy), draw_color, current_thickness, cv2.LINE_AA)
                    
                    current_stroke.append((cx, cy))
                    prevPoint = [cx, cy]
                    
                elif index_up and pinky_up:
                    # HOVERING MODE
                    if writing_active and stroke_active:
                        # Stroke just ended — Shape Recognition
                        if not ERASER_MODE:
                            shape_type, params = recognize_shape(current_stroke)
                            if shape_type is not None:
                                if imgCanvasPrev is not None:
                                    imgCanvas = imgCanvasPrev.copy()
                                
                                if shape_type == "CIRCLE":
                                    cx_s, cy_s, r_s = params
                                    cv2.circle(imgCanvas, (cx_s, cy_s), r_s, DRAW_COLOR, brush_thickness, cv2.LINE_AA)
                                elif shape_type in ["RECTANGLE", "TRIANGLE", "PENTAGON", "HEXAGON"]:
                                    cv2.drawContours(imgCanvas, [params], 0, DRAW_COLOR, brush_thickness, cv2.LINE_AA)
                                elif shape_type == "LINE":
                                    p1, p2 = params
                                    cv2.line(imgCanvas, p1, p2, DRAW_COLOR, brush_thickness, cv2.LINE_AA)
                                elif shape_type == "ELLIPSE":
                                    cv2.ellipse(imgCanvas, params, DRAW_COLOR, brush_thickness, cv2.LINE_AA)

                        undo_list.append(imgCanvas.copy())
                        if len(undo_list) > max_undos + 1:
                            undo_list.pop(0)
                        redo_list.clear()
                        stroke_active = False
                        current_stroke = []
                    
                    writing_active = False
                    gesture_text = "HOVERING"
                    prevPoint = None
                    cv2.circle(imgResult, (cx, cy), 15, (255, 255, 0), 2)
                
                else:
                    # Other gestures
                    if stroke_active:
                        undo_list.append(imgCanvas.copy())
                        if len(undo_list) > max_undos + 1:
                            undo_list.pop(0)
                        redo_list.clear()
                        stroke_active = False
                        current_stroke = []
                    writing_active = False
                    prevPoint = None
                    cv2.circle(imgResult, (cx, cy), 15, (255, 255, 0), 2)

            elif hand_type == "Left":  # LEFT HAND = SETTINGS
                # Get landmarks
                fingers, finger_dist = count_fingers_up(hand_lms, iw, ih, hand_type)
                
                lx = int(hand_lms[8].x * iw)
                ly = int(hand_lms[8].y * ih)
                
                # --- Swipe-to-Undo Tracking & Detection ---
                current_time = time.time()
                if len(left_hand_history) > 0:
                    prev_t = left_hand_history[-1][2]
                    if current_time - prev_t > 0.15:
                        left_hand_history = []
                
                left_hand_history.append((lx, ly, current_time))
                if len(left_hand_history) > 12:
                    left_hand_history.pop(0)
                
                if len(left_hand_history) >= 2:
                    x_end, y_end, t_end = left_hand_history[-1]
                    for x_start, y_start, t_start in left_hand_history[:-1]:
                        dt = t_end - t_start
                        if dt <= 0.3:
                            dx_left = x_start - x_end
                            dx_right = x_end - x_start
                            dy = abs(y_start - y_end)
                            
                            # 1. Swipe Left -> Clear Screen (with backup for restore)
                            if dx_left > 0.15 * iw and dy < 0.60 * dx_left:
                                if t_end - last_swipe_time > swipe_cooldown:
                                    pre_clear_canvas = imgCanvas.copy()
                                    pre_clear_undo_list = [state.copy() for state in undo_list]
                                    imgCanvas = np.zeros_like(img)
                                    undo_list = [imgCanvas.copy()]
                                    redo_list.clear()
                                    prevPoint = None
                                    stroke_active = False
                                    current_stroke = []
                                    toast_message = "CANVAS CLEARED"
                                    toast_timer = t_end
                                    print("Gesture Clear Screen Triggered!")
                                    last_swipe_time = t_end
                                    left_hand_history = []
                                    break
                            
                            # 2. Swipe Right -> Restore Cleared Canvas
                            elif dx_right > 0.15 * iw and dy < 0.60 * dx_right:
                                if t_end - last_swipe_time > swipe_cooldown:
                                    if pre_clear_canvas is not None:
                                        imgCanvas = pre_clear_canvas.copy()
                                        undo_list = [state.copy() for state in pre_clear_undo_list]
                                        pre_clear_canvas = None
                                        pre_clear_undo_list = None
                                        prevPoint = None
                                        stroke_active = False
                                        current_stroke = []
                                        toast_message = "CANVAS RESTORED"
                                        toast_timer = t_end
                                        print("Gesture Canvas Restore Triggered!")
                                    else:
                                        toast_message = "NOTHING TO RESTORE"
                                        toast_timer = t_end
                                        print("Gesture Restore - Nothing to Restore!")
                                    last_swipe_time = t_end
                                    left_hand_history = []
                                    break
                
                # Compute hover_tool_idx for toolbar highlight
                if ly < header_height:
                    hover_tool_idx = lx // (iw // len(TOOL_NAMES))

                # 1. Dynamic Brush Sizing (Thumb-Index distance) & Locking Gesture
                # Active when middle and ring are folded, and hand is below the toolbar
                if not fingers[2] and not fingers[3] and ly >= header_height:
                    if fingers[4]:  # Pinky finger extended = ADJUSTING
                        # Scale-invariant normalization using palm size (wrist landmark 0 to middle MCP landmark 9)
                        wx, wy = hand_lms[0].x * iw, hand_lms[0].y * ih
                        mx, my = hand_lms[9].x * iw, hand_lms[9].y * ih
                        palm_dist = np.sqrt((wx - mx)**2 + (wy - my)**2)
                        if palm_dist == 0:
                            palm_dist = 1.0
                        
                        norm_dist = finger_dist / palm_dist
                        # Map normalized distance (~0.2 to ~1.2) to brush thickness
                        new_thickness = int(np.interp(norm_dist, [0.2, 1.2], [2, 50]))
                        
                        # Prevent jitter: only update if change is at least 1 pixel
                        if abs(new_thickness - brush_thickness) >= 1:
                            brush_thickness = new_thickness

                        # Dynamic HUD Visual Feedback (Cyan for Adjusting)
                        tx_p, ty_p = int(hand_lms[4].x * iw), int(hand_lms[4].y * ih)
                        ix_p, iy_p = int(hand_lms[8].x * iw), int(hand_lms[8].y * ih)
                        
                        # Draw a connecting line between thumb tip and index tip
                        cv2.line(imgResult, (tx_p, ty_p), (ix_p, iy_p), (0, 255, 255), 2, cv2.LINE_AA)
                        cv2.circle(imgResult, (tx_p, ty_p), 6, (255, 0, 255), -1, cv2.LINE_AA)
                        cv2.circle(imgResult, (ix_p, iy_p), 6, (255, 0, 255), -1, cv2.LINE_AA)
                        
                        # Size label next to index tip
                        cv2.putText(imgResult, f"SIZE: {brush_thickness}", (ix_p + 15, iy_p), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2, cv2.LINE_AA)
                    else:  # Pinky finger folded = LOCKED
                        # Dynamic HUD Visual Feedback (Green for Locked)
                        tx_p, ty_p = int(hand_lms[4].x * iw), int(hand_lms[4].y * ih)
                        ix_p, iy_p = int(hand_lms[8].x * iw), int(hand_lms[8].y * ih)
                        
                        # Draw a thin green connecting line
                        cv2.line(imgResult, (tx_p, ty_p), (ix_p, iy_p), (0, 200, 0), 1, cv2.LINE_AA)
                        cv2.circle(imgResult, (tx_p, ty_p), 5, (0, 200, 0), -1, cv2.LINE_AA)
                        cv2.circle(imgResult, (ix_p, iy_p), 5, (0, 200, 0), -1, cv2.LINE_AA)
                        
                        # Size label next to index tip
                        cv2.putText(imgResult, f"SIZE: {brush_thickness} (LOCKED)", (ix_p + 15, iy_p), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 0), 2, cv2.LINE_AA)
                
                # Visual feedback preview for brush size on left side (always visible when Left hand is present)
                cv2.circle(imgResult, (50, ih-50), brush_thickness, DRAW_COLOR, -1)
                cv2.putText(imgResult, f"SIZE: {brush_thickness}", (20, ih-110), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                # 2. Tool Selection (Index finger over palette)
                if fingers[1] and ly < header_height:
                    num_tools_local = len(TOOL_NAMES)
                    tool_idx = lx // (iw // num_tools_local)
                    
                    if tool_idx < 4: # Colors
                        DRAW_COLOR = COLORS[tool_idx]
                        ERASER_MODE = False
                    elif tool_idx == 4: # Eraser
                        ERASER_MODE = True
                    elif tool_idx == 5: # Save
                        if time.time() - last_action_time > cooldown_duration:
                            save_drawing(imgResult)
                            last_action_time = time.time()
                    elif tool_idx == 6: # Invert Hand
                        if time.time() - last_action_time > cooldown_duration:
                            SWAP_HANDS = not SWAP_HANDS
                            print(f"Handedness Swapped: {SWAP_HANDS}")
                            last_action_time = time.time()
                
                # Left-hand controller cursor — magenta dot
                cv2.circle(imgResult, (lx, ly), 8, (255, 0, 255), cv2.FILLED, cv2.LINE_AA)
                cv2.circle(imgResult, (lx, ly), 10, (255, 255, 255), 1, cv2.LINE_AA)
    
    if not right_hand_this_frame:
        # Right hand left the frame — end stroke if active
        if stroke_active:
            if not ERASER_MODE:
                shape_type, params = recognize_shape(current_stroke)
                if shape_type is not None:
                    if imgCanvasPrev is not None:
                        imgCanvas = imgCanvasPrev.copy()
                    
                    if shape_type == "CIRCLE":
                        cx_s, cy_s, r_s = params
                        cv2.circle(imgCanvas, (cx_s, cy_s), r_s, DRAW_COLOR, brush_thickness, cv2.LINE_AA)
                    elif shape_type in ["RECTANGLE", "TRIANGLE", "PENTAGON", "HEXAGON"]:
                        cv2.drawContours(imgCanvas, [params], 0, DRAW_COLOR, brush_thickness, cv2.LINE_AA)
                    elif shape_type == "LINE":
                        p1, p2 = params
                        cv2.line(imgCanvas, p1, p2, DRAW_COLOR, brush_thickness, cv2.LINE_AA)
                    elif shape_type == "ELLIPSE":
                        cv2.ellipse(imgCanvas, params, DRAW_COLOR, brush_thickness, cv2.LINE_AA)

            undo_list.append(imgCanvas.copy())
            if len(undo_list) > max_undos + 1:
                undo_list.pop(0)
            redo_list.clear()
            stroke_active = False
            current_stroke = []

        prevPoint = None
        filter_x.reset()
        filter_y.reset()
    
    # --- Antigravity HUD: Floating Status Pill ---
    draw_floating_status(
        imgResult, gesture_text, right_fingertip,
        hand_visible=right_hand_this_frame, frame_count=frame_count)

    # --- Antigravity HUD: Stats Overlay (bottom-left) ---
    active_hand_label = "RIGHT" if not SWAP_HANDS else "SWAPPED"
    draw_stats_overlay(imgResult, fps, brush_thickness, len(undo_list) - 1, active_hand_label)

    # --- Antigravity HUD: HUD Toast Notifications ---
    if toast_message is not None:
        elapsed = time.time() - toast_timer
        if elapsed < 1.5:
            # Determine fade-out alpha
            if elapsed > 1.0:
                fade_alpha = (1.5 - elapsed) / 0.5
            else:
                fade_alpha = 1.0
            
            # Draw Toast centered horizontally at y=120 (just below header toolbar)
            font = cv2.FONT_HERSHEY_DUPLEX
            font_scale = 0.65
            (tw, th), baseline = cv2.getTextSize(toast_message, font, font_scale, 2)
            
            pad_x = 24
            pad_y = 14
            w = tw + pad_x * 2
            h = th + pad_y * 2
            x = (iw - w) // 2
            y = 120
            
            # Ensure ROI is fully within bounds
            if x >= 0 and y >= 0 and x + w <= iw and y + h <= ih:
                # ROI slice and copy
                toast_roi = imgResult[y:y+h, x:x+w].copy()
                
                # Determine glow color
                if "UNDO" in toast_message:
                    glow_color = (0, 255, 255)      # Cyan for Undo
                elif "REDO" in toast_message:
                    glow_color = (255, 0, 255)      # Magenta for Redo
                elif "CLEARED" in toast_message:
                    glow_color = (0, 60, 255)       # Red for Clear Screen
                elif "RESTORE" in toast_message:
                    glow_color = (0, 165, 255)      # Amber/Orange for Restore
                else:
                    glow_color = (0, 200, 80)       # Green for Save
                
                # Render glass rect
                draw_glass_rect(toast_roi, 0, 0, w, h, color=GLASS_BG, alpha=0.5, radius=12, glow_color=glow_color)
                
                # Render text
                tx = (w - tw) // 2
                ty = (h + th) // 2
                cv2.putText(toast_roi, toast_message, (tx + 1, ty + 1), font, font_scale, (0, 0, 0), 2, cv2.LINE_AA)
                cv2.putText(toast_roi, toast_message, (tx, ty), font, font_scale, glow_color, 2, cv2.LINE_AA)
                
                # Blend back
                cv2.addWeighted(toast_roi, fade_alpha, imgResult[y:y+h, x:x+w], 1.0 - fade_alpha, 0, imgResult[y:y+h, x:x+w])
        else:
            toast_message = None

    # --- Merge Canvas ---
    imgGray = cv2.cvtColor(imgCanvas, cv2.COLOR_BGR2GRAY)
    _, imgInv = cv2.threshold(imgGray, 1, 255, cv2.THRESH_BINARY_INV)
    imgInv = cv2.cvtColor(imgInv, cv2.COLOR_GRAY2BGR)
    imgResult = cv2.bitwise_and(imgResult, imgInv)
    imgResult = cv2.bitwise_or(imgResult, imgCanvas)
    
    cv2.imshow("Ink-in-Air Gesture Drawing System", imgResult)
    
    # --- Keyboard Controls ---
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('c'):
        pre_clear_canvas = imgCanvas.copy()
        pre_clear_undo_list = [state.copy() for state in undo_list]
        imgCanvas = np.zeros_like(img)
        undo_list = [imgCanvas.copy()]
        redo_list.clear()
        prevPoint = None
        toast_message = "CANVAS CLEARED"
        toast_timer = time.time()
    elif key == ord('z'):
        if len(undo_list) > 1:
            undone_state = undo_list.pop()
            redo_list.append(undone_state)
            imgCanvas = undo_list[-1].copy()
            prevPoint = None
            toast_message = "UNDO"
            toast_timer = time.time()
    elif key == ord('x'):
        if len(redo_list) > 0:
            undone_state = redo_list.pop()
            undo_list.append(undone_state)
            imgCanvas = undone_state.copy()
            prevPoint = None
            toast_message = "REDO"
            toast_timer = time.time()
    elif key == ord('s'):
        save_drawing(imgResult)
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