"""
Camera Selector: Shows a live preview from each detected camera
so you can visually identify which index matches which device.
Press any key to move to the next camera. Press 'q' to quit.
"""
import cv2

print("=== Camera Identification Tool ===\n")

for i in range(5):
    cap = cv2.VideoCapture(i)
    if not cap.isOpened():
        print(f"Index {i}: Not available")
        cap.release()
        continue
    
    # Read the camera's actual resolution
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"Index {i}: Active ({w}x{h}) — Showing preview...")
    print("   Press any key to close this preview, 'q' to quit.\n")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Label the frame so you can see which index you're looking at
        cv2.putText(frame, f"Camera Index: {i} ({w}x{h})", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        cv2.putText(frame, "Press any key for next, 'q' to quit", (10, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        cv2.imshow("Camera Preview", frame)
        key = cv2.waitKey(1) & 0xFF
        if key != 255:  # Any key pressed
            if key == ord('q'):
                cap.release()
                cv2.destroyAllWindows()
                print("Quit.")
                exit()
            break
    
    cap.release()
    cv2.destroyAllWindows()

print("\n=== Done. Update CAMERA_INDEX in drawing.py with your chosen index. ===")
