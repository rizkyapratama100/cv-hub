"""
Video processing router.

POST /process-video
  - Accepts a video file upload and a processor name
  - Streams processed frames back as newline-delimited JSON (NDJSON)
  - Each line: {"frame": "<base64 JPEG>", "index": N, "total": N}
  - Final line: {"done": true, "total": N}

GET /processors
  - Returns list of available processors with metadata
"""

import base64
import json
import tempfile
import os
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.processors import PROCESSORS, PROCESSOR_META

router = APIRouter()

# Safety limits (important for 512MB RAM on Lightsail)
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024   # 50 MB
MAX_FRAMES = 300                           # Cap at ~10 seconds at 30fps
TARGET_FPS = 10                            # Process every Nth frame to hit this
JPEG_QUALITY = 70                          # Lower = smaller payload, faster streaming


@router.get("/processors")
def list_processors():
    """Return available processors for the frontend dropdown."""
    return {"processors": PROCESSOR_META}


def _encode_frame(frame: np.ndarray) -> str:
    """Encode a BGR numpy frame to a base64 JPEG string."""
    _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    return base64.b64encode(buffer).decode("utf-8")


def _frame_generator(video_path: str, processor_fn, source_fps: float):
    """
    Generator that yields NDJSON-encoded processed frames.
    Skips frames to target TARGET_FPS to reduce memory/CPU pressure.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        yield json.dumps({"error": "Could not open video file"}) + "\n"
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_fps = cap.get(cv2.CAP_PROP_FPS) or source_fps or 30.0

    # Calculate frame skip to approximate TARGET_FPS
    frame_skip = max(1, round(video_fps / TARGET_FPS))

    # Cap total output frames
    output_frame_count = min(MAX_FRAMES, total_frames // frame_skip)

    frame_index = 0
    output_index = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Only process every Nth frame
            if frame_index % frame_skip == 0 and output_index < MAX_FRAMES:
                try:
                    processed = processor_fn(frame)
                    encoded = _encode_frame(processed)
                    payload = json.dumps({
                        "frame": encoded,
                        "index": output_index,
                        "total": output_frame_count,
                    })
                    yield payload + "\n"
                    output_index += 1
                except Exception as e:
                    yield json.dumps({"error": f"Frame processing error: {str(e)}"}) + "\n"
                    break

            frame_index += 1

        yield json.dumps({"done": True, "total": output_index}) + "\n"

    finally:
        cap.release()


@router.post("/process-image")
async def process_image(
    file: UploadFile = File(...),
    processor: str = Form(default="passthrough"),
):
    """
    Upload a single image and return the processed result as a base64 JPEG.
    Response: {"frame": "<base64 JPEG>"}
    """
    if processor not in PROCESSORS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown processor '{processor}'. Available: {list(PROCESSORS.keys())}",
        )

    allowed_image_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type and file.content_type not in allowed_image_types:
        raise HTTPException(status_code=400, detail=f"Unsupported image type '{file.content_type}'.")

    content = await file.read(MAX_FILE_SIZE_BYTES + 1)
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 50MB limit.")

    # Decode image directly from bytes (no temp file needed for images)
    arr = np.frombuffer(content, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Could not decode image file.")

    try:
        processed = PROCESSORS[processor](frame)
        encoded = _encode_frame(processed)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

    return {"frame": encoded}


@router.post("/process-video")
async def process_video(
    file: UploadFile = File(...),
    processor: str = Form(default="passthrough"),
):
    """
    Upload a video file and stream back processed frames as NDJSON.
    Each response chunk is a JSON object terminated by a newline.
    """
    # Validate processor name
    if processor not in PROCESSORS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown processor '{processor}'. Available: {list(PROCESSORS.keys())}",
        )

    # Validate content type (basic check — also validated by magic bytes below)
    allowed_content_types = {"video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"}
    if file.content_type and file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'.",
        )

    # Read file into memory with size cap
    content = await file.read(MAX_FILE_SIZE_BYTES + 1)
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 50MB limit.")

    # Validate magic bytes (MP4: ftyp, WebM: \x1a\x45\xdf\xa3, AVI: RIFF)
    is_valid = (
        content[4:8] == b"ftyp"          # MP4/MOV
        or content[:4] == b"\x1a\x45\xdf\xa3"  # WebM/MKV
        or content[:4] == b"RIFF"         # AVI
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail="File does not appear to be a valid video.")

    processor_fn = PROCESSORS[processor]

    # Write to temp file (OpenCV needs a file path, not a buffer)
    suffix = Path(file.filename or "upload.mp4").suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    def cleanup_and_stream():
        try:
            yield from _frame_generator(tmp_path, processor_fn, source_fps=30.0)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return StreamingResponse(
        cleanup_and_stream(),
        media_type="application/x-ndjson",
        headers={"X-Content-Type-Options": "nosniff"},
    )
