import cv2

def test_cameras():
    print("Searching for available cameras...")
    indices = []
    # Test first 5 indices (usually enough for most Mac setups)
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"[SUCCESS] Index {i}: Camera is working.")
                indices.append(i)
            else:
                print(f"[WARNING] Index {i}: Camera opened but failed to read frame.")
            cap.release()
        else:
            print(f"[INFO] Index {i}: No camera found.")
    
    if indices:
        print(f"\nAvailable Indices: {indices}")
        print("\nTo use Continuity Camera (iPhone):")
        print("1. Ensure iPhone is unlocked and nearby.")
        print("2. Run this script again. The iPhone usually appears as index 1 or 2.")
        print("3. Once you identify the index, update CAMERA_INDEX in drawing.py.")
    else:
        print("\nNo working cameras found. Please check your system permissions.")

if __name__ == "__main__":
    test_cameras()
