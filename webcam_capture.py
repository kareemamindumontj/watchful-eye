from datetime import datetime
from config import WEBCAM_DIR

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

def capture_photo():
    if not HAS_CV2:
        return None
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        return None
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = WEBCAM_DIR / f"boot_{ts}.jpg"
    cv2.imwrite(str(path), frame)
    return path
