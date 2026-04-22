import cv2
import numpy as np
import time
import json
import os

# --- Configuration ---
CONFIG_FILE = "pen_config.json"

def load_calibration():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                v = json.load(f)
                color = [v[0], v[1], v[2], v[3], v[4], v[5]]
                hue_range = color[3] - color[0]
                sat_min = color[1]
                if hue_range > 60 or sat_min < 50:
                    print("[WARNING] Your calibration is too broad (H range > 60 or Sat Min < 50).")
                    print("[WARNING] This will cause the tracker to pick up skin, walls, and background.")
                    print("[WARNING] Run picker.py and narrow your color range for accuracy.")
                return [color]
        except:
            pass
    return [[0, 136, 115, 25, 174, 255]]

# 0 = Built-in Mac Webcam | 1 = Apple Continuity Camera (iPhone)
CAMERA_INDEX = 0
cap = cv2.VideoCapture(CAMERA_INDEX)

# Target Color (HSV): Loaded automatically from picker.py
myColors = load_calibration()

# Drawing Ink Color (BGR format): Red
myColorValues = [[0, 0, 255]]

# --- Creative Enhancement Variables ---
brush_thickness = 10
undo_list = []
max_undos = 10
# Tracks if a pen was detected in the previous frame to trigger undo snapshots
stroke_active = [False] * len(myColors)

# Current line segments tracking: [x, y] for each color in myColors
prevPoints = [None] * len(myColors)
prev_time = 0

# Pen Lift State
writing_active = True

# Persistent canvas to store the drawing
imgCanvas = None

# --- Kalman Filter Setup ---
kf_list = []
for _ in range(len(myColors)):
    kf = cv2.KalmanFilter(4, 2)
    kf.transitionMatrix = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32)
    kf.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float32)
    kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.2
    kf_list.append(kf)

def getContours(img):
    contours, hierarchy = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    x, y, w, h = 0, 0, 0, 0
    best_area = 0
    best_box = None
    # Track the LARGEST valid contour only, ignoring smaller false positives
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 1500 and area > best_area:  # Raised threshold to 1500
            best_area = area
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            best_box = cv2.boundingRect(approx)
    if best_box:
        x, y, w, h = best_box
        return x + w // 2, y + h // 2  # Use center of object, not top edge
    return x, y

def findColor(img, myColors, myColorValues, imgResult):
    imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    newPoints = []
    for count, color in enumerate(myColors):
        lower = np.array(color[0:3])
        upper = np.array(color[3:6])
        mask = cv2.inRange(imgHSV, lower, upper)
        
        # Morphological Opening to remove small noise dots
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.erode(mask, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        x, y = getContours(mask)
        
        if x != 0 and y != 0:
            # If this is a new stroke (first time seeing the pen), reset the Kalman state
            # This eliminates 'lag' and 'jumps' at the start of a line
            if prevPoints[count] is None:
                kf_list[count].statePre = np.array([[np.float32(x)], [np.float32(y)], [0], [0]], dtype=np.float32)
                kf_list[count].statePost = np.array([[np.float32(x)], [np.float32(y)], [0], [0]], dtype=np.float32)

            # Applying Kalman Prediction & Correction
            kf_list[count].predict()
            measurement = np.array([[np.float32(x)], [np.float32(y)]])
            corrected = kf_list[count].correct(measurement)
            cx, cy = int(corrected[0][0]), int(corrected[1][0])
            
            # Show tracking cursor style based on mode
            if writing_active:
                cv2.circle(imgResult, (cx, cy), 15, myColorValues[count], cv2.FILLED)
            else:
                cv2.circle(imgResult, (cx, cy), 15, (255, 255, 0), 2) # Hollow yellow ring for hover
            
            newPoints.append([cx, cy, count])
    return newPoints

print(f"Starting Camera {CAMERA_INDEX}...")
if os.path.exists(CONFIG_FILE):
    print(f"Calibration loaded from {CONFIG_FILE}")
else:
    print("No calibration found, using default values.")
print("Controls: 'z'=Undo, 'c'=Clear, 'q'=Quit, Up/Down=Brush Size")

while True:
    success, img = cap.read()
    if not success:
        break
    
    img = cv2.flip(img, 1)
    # Apply Gaussian Blur to reduce pixel noise
    img = cv2.GaussianBlur(img, (5, 5), 0)
    imgResult = img.copy()

    if imgCanvas is None:
        imgCanvas = np.zeros_like(img)
        # Seed initial undo state
        undo_list.append(imgCanvas.copy())
    
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time) if prev_time != 0 else 0
    prev_time = curr_time
    
    # UI Overlay
    cv2.putText(imgResult, f'FPS: {int(fps)}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    cv2.putText(imgResult, f'Brush Size: {brush_thickness}', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    cv2.putText(imgResult, f'History: {len(undo_list)-1}', (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    
    # Mode Status Indicator
    mode_text = "[ MODE: WRITING ]" if writing_active else "[ MODE: HOVERING ]"
    mode_color = (0, 255, 0) if writing_active else (0, 0, 255)
    cv2.putText(imgResult, mode_text, (imgResult.shape[1] - 250, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, mode_color, 2)

    newPoints = findColor(img, myColors, myColorValues, imgResult)
    
    colors_seen = set()
    if len(newPoints) != 0:
        for newP in newPoints:
            x, y, colorId = newP
            colors_seen.add(colorId)
            
            # If a new stroke starts, we'll mark it as active
            stroke_active[colorId] = True
            
            if writing_active and prevPoints[colorId] is not None:
                dist = np.linalg.norm(np.array([x, y]) - np.array(prevPoints[colorId]))
                # Only draw if movement is real (> 3px) and not a tracker jump (< 100px)
                # The minimum movement (3px) prevents ghost lines when pen is stationary
                if 3 < dist < 100:
                    cv2.line(imgCanvas, (prevPoints[colorId][0], prevPoints[colorId][1]), (x, y), myColorValues[colorId], brush_thickness)
            prevPoints[colorId] = [x, y]
            
    # Handle stroke breaks and Undo snapshots
    for i in range(len(myColors)):
        if i not in colors_seen:
            # If the pen just disappeared, it means a stroke just ended. Take a snapshot.
            if stroke_active[i]:
                undo_list.append(imgCanvas.copy())
                if len(undo_list) > max_undos + 1:
                    undo_list.pop(0)
                stroke_active[i] = False
            prevPoints[i] = None

    # Merge Canvas
    imgGray = cv2.cvtColor(imgCanvas, cv2.COLOR_BGR2GRAY)
    _, imgInv = cv2.threshold(imgGray, 1, 255, cv2.THRESH_BINARY_INV)
    imgInv = cv2.cvtColor(imgInv, cv2.COLOR_GRAY2BGR)
    imgResult = cv2.bitwise_and(imgResult, imgInv)
    imgResult = cv2.bitwise_or(imgResult, imgCanvas)
        
    cv2.imshow("MajorProject - Pro Suite", imgResult)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('c'):
        imgCanvas = np.zeros_like(img)
        undo_list = [imgCanvas.copy()]
        prevPoints = [None] * len(myColors)
    elif key == ord('z'):
        if len(undo_list) > 1:
            undo_list.pop() # Remove current state
            imgCanvas = undo_list[-1].copy() # Restore previous
            prevPoints = [None] * len(myColors)
    # Up Arrow (Mac/Standard)
    elif key == 0 or key == 82: # Up
        brush_thickness = min(brush_thickness + 2, 50)
    # Down Arrow (Mac/Standard)
    elif key == 1 or key == 84: # Down
        brush_thickness = max(brush_thickness - 2, 2)
    # Fallback for thickness if arrows fail
    elif key == ord('w'):
        brush_thickness = min(brush_thickness + 2, 50)
    elif key == ord('s'):
        brush_thickness = max(brush_thickness - 2, 2)
    elif key == ord(' '):
        writing_active = not writing_active
        # Clear previous points on toggle to ensure no "connector lines" when resuming
        prevPoints = [None] * len(myColors)
        print(f"Mode changed: {'WRITING' if writing_active else 'HOVERING'}")

cap.release()
cv2.destroyAllWindows()