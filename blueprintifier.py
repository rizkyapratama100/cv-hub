"""Blueprintifier CV project scaffold.

This module is intentionally CV-hub compatible from the start. The platform
will call ``process_frame(frame)`` with a BGR uint8 NumPy array and expects a
BGR uint8 NumPy array in return.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


Frame = np.ndarray


def isolate_central_object(frame: Frame) -> Frame:
    """TODO: Isolate the central object from the frame.

    Expected future responsibility:
    - Identify the likely foreground/central object.
    - Suppress or remove background content.
    - Return an image/mask/intermediate representation useful for edge work.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    bitNot = cv2.bitwise_not(gray)
    
    # OPTION 1: GAUSSIAN BLUR
    gausBlur = cv2.GaussianBlur(bitNot, (21, 21), 0)
    # return gausBlur
    
    # OPTION 2: BILATERAL FILTER
    biFilt = cv2.bilateralFilter(gausBlur, 9, 75, 75)
    return biFilt

def extract_edges_and_contours(frame: Frame) -> Frame:
    """TODO: Extract structural edges and contours from the object.

    Expected future responsibility:
    - Detect relevant object edges.
    - Clean noisy contours.
    - Preserve details that should appear in the blueprint output.
    """
    
    # OPTION 3: CANNY
    # Apply Canny Edge Detector
    edges = cv2.Canny(frame, threshold1=25, threshold2=50)

    return edges


def render_blueprint_style(frame: Frame) -> Frame:
    """TODO: Render the processed object as a blueprint-style image.

    The visual language, colors, line weights, labels, and annotations are
    intentionally left for the CV implementation pass.
    """
    if frame.ndim == 3:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    else:
        gray = frame

    _, edges = cv2.threshold(gray, 32, 255, cv2.THRESH_BINARY)

    kernel = np.ones((2, 2), dtype=np.uint8)
    edges = cv2.dilate(edges, kernel, iterations=1)

    height, width = edges.shape
    blueprint = np.full((height, width, 3), (80, 35, 10), dtype=np.uint8)
    _draw_blueprint_grid(blueprint)

    blueprint[edges > 0] = (255, 255, 255)
    _draw_blueprint_border(blueprint)

    return blueprint


def _draw_blueprint_grid(canvas: Frame, spacing: int = 32) -> None:
    """Draw a subtle drafting grid onto a BGR blueprint canvas."""
    if spacing <= 0:
        return

    height, width = canvas.shape[:2]
    minor_color = (105, 55, 25)
    major_color = (135, 75, 35)
    major_interval = spacing * 4

    for x in range(0, width, spacing):
        color = major_color if x % major_interval == 0 else minor_color
        cv2.line(canvas, (x, 0), (x, height - 1), color, 1)

    for y in range(0, height, spacing):
        color = major_color if y % major_interval == 0 else minor_color
        cv2.line(canvas, (0, y), (width - 1, y), color, 1)


def _draw_blueprint_border(canvas: Frame) -> None:
    """Draw a simple technical drawing border around a BGR blueprint canvas."""
    height, width = canvas.shape[:2]
    if height < 2 or width < 2:
        return

    margin = max(8, min(height, width) // 40)
    margin = min(margin, (width - 1) // 2, (height - 1) // 2)
    border_color = (180, 130, 75)
    tick_color = (220, 190, 140)
    tick_length = max(8, min(height, width) // 24)

    top_left = (margin, margin)
    bottom_right = (width - margin - 1, height - margin - 1)
    cv2.rectangle(canvas, top_left, bottom_right, border_color, 1)

    corners = (
        (margin, margin, 1, 1),
        (width - margin - 1, margin, -1, 1),
        (margin, height - margin - 1, 1, -1),
        (width - margin - 1, height - margin - 1, -1, -1),
    )
    for x, y, x_direction, y_direction in corners:
        cv2.line(canvas, (x, y), (x + x_direction * tick_length, y), tick_color, 1)
        cv2.line(canvas, (x, y), (x, y + y_direction * tick_length), tick_color, 1)


def process_frame(frame: Frame) -> Frame:
    """Process one BGR uint8 frame and return one BGR uint8 frame.

    This is the integration entrypoint expected by the CV hub. The current
    implementation only wires the future pipeline stages and protects the
    platform from malformed output or unhandled exceptions.
    """
    try:
        source = _validate_input_frame(frame)
        isolated = isolate_central_object(source)
        edges = extract_edges_and_contours(isolated)
        output = render_blueprint_style(edges)
        return _normalize_output_frame(output, source.shape)
    except Exception:
        return _fallback_frame(frame)


def _validate_input_frame(frame: Frame) -> Frame:
    if not isinstance(frame, np.ndarray):
        raise TypeError("frame must be a numpy array")
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("frame must have shape (H, W, 3)")
    if frame.dtype != np.uint8:
        raise TypeError("frame must have dtype uint8")
    return frame


def _normalize_output_frame(frame: Frame, expected_shape: tuple[int, int, int]) -> Frame:
    if not isinstance(frame, np.ndarray):
        raise TypeError("processed frame must be a numpy array")

    if frame.ndim == 2:
        frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError("processed frame must have shape (H, W, 3)")

    if frame.shape != expected_shape:
        frame = cv2.resize(frame, (expected_shape[1], expected_shape[0]))

    if frame.dtype != np.uint8:
        frame = np.clip(frame, 0, 255).astype(np.uint8)

    return frame


def _fallback_frame(frame: Frame) -> Frame:
    if isinstance(frame, np.ndarray) and frame.ndim == 3 and frame.shape[2] == 3:
        if frame.dtype == np.uint8:
            return frame
        return np.clip(frame, 0, 255).astype(np.uint8)

    return np.zeros((1, 1, 3), dtype=np.uint8)


def _run_cli(input_path: Path, output_path: Path) -> None:
    image = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {input_path}")

    output = process_frame(image)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), output):
        raise OSError(f"Could not write image: {output_path}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Blueprintifier on one image.")
    parser.add_argument("input", type=Path, help="Path to an input image.")
    parser.add_argument("output", type=Path, help="Path where the output image will be written.")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    _run_cli(args.input, args.output)
