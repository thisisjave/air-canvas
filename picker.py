import cv2
import numpy as np
import json
import os

# --- Configuration ---
# 0 = Built-in Mac Webcam | 1 = Apple Continuity Camera (iPhone)
CAMERA_INDEX = 0
CONFIG_FILE = "pen_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return [0, 0, 0, 179, 255, 255] # Defaults: HueMin, SatMin, ValMin, HueMax, SatMax, ValMax

def empty(a):
    pass

cap = cv2.VideoCapture(CAMERA_INDEX)
cv2.namedWindow("TrackBars")
cv2.resizeWindow("TrackBars", 640, 240)

# Load existing values
init_vals = load_config()

# Initializing sliders with saved or default values
cv2.createTrackbar("Hue Min", "TrackBars", init_vals[0], 179, empty)
cv2.createTrackbar("Hue Max", "TrackBars", init_vals[3], 179, empty)
cv2.createTrackbar("Sat Min", "TrackBars", init_vals[1], 255, empty)
cv2.createTrackbar("Sat Max", "TrackBars", init_vals[4], 255, empty)
cv2.createTrackbar("Val Min", "TrackBars", init_vals[2], 255, empty)
cv2.createTrackbar("Val Max", "TrackBars", init_vals[5], 255, empty)

print(f"Starting Picker on Camera {CAMERA_INDEX}...")
print("Controls: 's' to Save and Quit, 'q' to Quit without saving.")

while True:
    success, img = cap.read()
    if not success:
        print("Waiting for stream or camera failed...")
        break

    imgHSV = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    h_min = cv2.getTrackbarPos("Hue Min", "TrackBars")
    h_max = cv2.getTrackbarPos("Hue Max", "TrackBars")
    s_min = cv2.getTrackbarPos("Sat Min", "TrackBars")
    s_max = cv2.getTrackbarPos("Sat Max", "TrackBars")
    v_min = cv2.getTrackbarPos("Val Min", "TrackBars")
    v_max = cv2.getTrackbarPos("Val Max", "TrackBars")
    
    lower = np.array([h_min, s_min, v_min])
    upper = np.array([h_max, s_max, v_max])
    mask = cv2.inRange(imgHSV, lower, upper)
    
    imgResult = cv2.bitwise_and(img, img, mask=mask)
    stacked = np.hstack([img, imgResult])
    
    cv2.imshow("Original vs Isolated Color", stacked)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('s'):
        # Save values to JSON
        config_data = [h_min, s_min, v_min, h_max, s_max, v_max]
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f)
        print(f"Values saved to {CONFIG_FILE}!")
        break
    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()