"""
CV processor module.

Each processor is a callable that accepts a BGR numpy frame and returns
a processed BGR numpy frame. This interface is intentional — when real
CV projects are integrated they simply need to match this signature.
"""

from typing import Callable
import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Placeholder processors (simple OpenCV operations)
# ---------------------------------------------------------------------------

def grayscale(frame: np.ndarray) -> np.ndarray:
    """Convert frame to grayscale (returned as 3-channel for uniform display)."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def edge_detection(frame: np.ndarray) -> np.ndarray:
    """Canny edge detection on grayscale, returned as 3-channel."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, threshold1=50, threshold2=150)
    return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)


def blur(frame: np.ndarray) -> np.ndarray:
    """Gaussian blur."""
    return cv2.GaussianBlur(frame, (21, 21), 0)


def threshold(frame: np.ndarray) -> np.ndarray:
    """Binary threshold on grayscale, returned as 3-channel."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)


def passthrough(frame: np.ndarray) -> np.ndarray:
    """No-op — returns the original frame unchanged."""
    return frame


# ---------------------------------------------------------------------------
# Registry: maps filter name (used in API) to processor callable
# ---------------------------------------------------------------------------

PROCESSORS: dict[str, Callable[[np.ndarray], np.ndarray]] = {
    "passthrough": passthrough,
    "grayscale": grayscale,
    "edge_detection": edge_detection,
    "blur": blur,
    "threshold": threshold,
}

# Human-readable metadata for the frontend dropdown
PROCESSOR_META: list[dict] = [
    {
        "id": "passthrough",
        "label": "None (Original)",
        "description": "No processing applied — shows the original video.",
    },
    {
        "id": "grayscale",
        "label": "Grayscale",
        "description": "Converts the video to grayscale using OpenCV's BGR→GRAY conversion.",
    },
    {
        "id": "edge_detection",
        "label": "Edge Detection",
        "description": "Applies Canny edge detection to highlight object boundaries.",
    },
    {
        "id": "blur",
        "label": "Gaussian Blur",
        "description": "Applies a Gaussian blur to smooth out the image.",
    },
    {
        "id": "threshold",
        "label": "Threshold",
        "description": "Applies binary thresholding to produce a black-and-white mask.",
    },
]
