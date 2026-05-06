import cv2 
from .config import CAMERA_INDEX

_camera : cv2.VideoCapture | None = None # Global variable to hold the camera instance in memory: it means that the camera will be opened only once and reused across the application

def open_camera() -> None:
    global _camera
    _camera = cv2.VideoCapture(CAMERA_INDEX) # Open the camera
    if not _camera.isOpened():
        raise RuntimeError(f"Cannot open camera at index {CAMERA_INDEX}")

def get_camera() -> cv2.VideoCapture:
    if _camera is None:
        print("Camera has not been opened. Trying to open it now...")
        try:
            open_camera() # Try to open the camera again
        except RuntimeError as e:
            raise RuntimeError(f"Failed to open camera: {e}")
    return _camera

def close_camera() -> None:
    global _camera
    if _camera is not None:
        _camera.release()
        _camera = None
