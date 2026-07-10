# Integrating CV Projects into CV Showcase

This document explains how to add a new Computer Vision project to the hub.
The integration is intentionally minimal — your CV project only needs to expose
a single function. Everything else (file handling, streaming, frontend display,
error handling) is handled by the platform.

---

## How It Works

The platform passes frames from uploaded images and videos to your CV function
one at a time. Your function receives a raw image frame, processes it, and
returns the result. The platform handles:

- Accepting file uploads from the browser
- Decoding video into frames and streaming results back
- Displaying the original and processed output side-by-side
- All error handling, timeouts, and memory management

---

## The Interface Contract

Your CV project must expose exactly one function with this signature:

```python
import numpy as np

def process_frame(frame: np.ndarray) -> np.ndarray:
    ...
```

**Input:** A single video/image frame as a NumPy array in **BGR format**
(OpenCV's default), shape `(H, W, 3)`, dtype `uint8`.

**Output:** A processed frame as a NumPy array, also **BGR format**,
shape `(H, W, 3)`, dtype `uint8`.

That's it. The function name does not have to be `process_frame` — you can
name it anything and register it under any ID (see step 2 below).

---

## Step-by-Step Integration

### Step 1 — Write your processor file

Create a file at `backend/app/cv_projects/your_project_name.py`.

Example for a hypothetical dice counter:

```python
# backend/app/cv_projects/dice_counter.py
import cv2
import numpy as np


def process_frame(frame: np.ndarray) -> np.ndarray:
    """
    Detect dice in the frame and draw bounding boxes + dot count overlays.
    """
    # ... your CV logic here ...
    return annotated_frame
```

Keep the file self-contained. If your project has helper functions or
sub-modules, put them in the same directory.

### Step 2 — Register it in processors.py

Open `backend/app/processors.py` and add two entries:

```python
# 1. Import your function
from .cv_projects.dice_counter import process_frame as dice_counter_fn

# 2. Add to the PROCESSORS registry
PROCESSORS: dict[str, Callable[[np.ndarray], np.ndarray]] = {
    "passthrough": passthrough,
    "grayscale": grayscale,
    # ... existing entries ...
    "dice_counter": dice_counter_fn,   # ← add this
}

# 3. Add metadata for the frontend dropdown
PROCESSOR_META: list[dict] = [
    # ... existing entries ...
    {
        "id": "dice_counter",          # must match the key in PROCESSORS
        "label": "Dice Counter",       # shown in the dropdown
        "description": "Detects dice in the frame and counts the total value shown.",
    },
]
```

### Step 3 — Add dependencies

If your project requires Python packages not already in `requirements.txt`,
add them with pinned versions:

```
# requirements.txt
torch==2.5.1          # example
torchvision==0.20.1   # example
```

Check what's already installed before adding anything:

```
fastapi, uvicorn, python-multipart, opencv-python-headless, numpy, Pillow
```

### Step 4 — Test locally

```bash
docker compose up --build
```

Open `http://localhost:5173`, select your new filter from the dropdown,
upload a test image or video, and verify the output looks correct.

### Step 5 — Deploy

```bash
# On the Lightsail instance
cd ~/cv-showcase
bash deploy.sh
```

The frontend on Cloudflare Pages fetches the processor list from the backend
at runtime — no frontend changes or redeployment needed.

---

## Requirements

Your `process_frame` function must:

- **Accept BGR numpy arrays.** OpenCV reads frames in BGR order, not RGB.
  If your model expects RGB, convert inside your function:
  ```python
  rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
  ```

- **Return a BGR numpy array** of shape `(H, W, 3)` and dtype `uint8`.
  If your output is grayscale, single-channel, or float, convert it before
  returning:
  ```python
  # Grayscale → 3-channel BGR
  return cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)

  # Float [0.0, 1.0] → uint8
  return (result * 255).astype(np.uint8)
  ```

- **Be stateless between frames.** Each call to `process_frame` is
  independent. The platform does not guarantee call order or continuity
  between frames (frames are skipped to hit target FPS).
  If your algorithm requires temporal context (e.g. optical flow,
  tracking), you need to handle state internally with care — see the
  limitations section below.

- **Not raise unhandled exceptions.** Wrap risky operations in try/except
  and return a fallback frame (e.g. the original) rather than crashing.
  A crash inside `process_frame` terminates the entire streaming response
  for that upload.

---

## Limitations

These are hard constraints imposed by the platform and hosting environment.
Design your CV projects with these in mind.

### Memory — 512MB RAM (production), upgradeable to 1GB

The Lightsail instance has limited RAM. The platform enforces a container
memory cap of ~400MB to leave headroom for the OS.

**What this means for your project:**
- Loading large model weights at request time will likely cause OOM crashes.
  Load models once at module import time (module-level singleton), not inside
  `process_frame`.
  ```python
  # Good — loaded once when the server starts
  _model = load_my_model("weights.pth")

  def process_frame(frame):
      return _model.predict(frame)

  # Bad — reloaded on every frame
  def process_frame(frame):
      model = load_my_model("weights.pth")   # OOM risk
      return model.predict(frame)
  ```
- Keep model weights under ~200MB for safe operation on the current plan.
  If your model is larger, upgrade the Lightsail plan to 2GB RAM ($10/month)
  before integrating.
- NumPy arrays for a 1080p frame are ~6MB each. Processing multiple copies
  of a frame simultaneously is fine; holding many frames in memory is not.

### CPU — 2 shared vCPUs, no GPU

The server has no GPU. All inference runs on CPU.

**What this means for your project:**
- Traditional CV (OpenCV operations, classical algorithms) will be fast.
- Lightweight neural networks (MobileNet, TinyYOLO, small transformers) are
  feasible but will be slow (~1-5 FPS effective throughput).
- Heavy models (ResNet-50+, full YOLO, SAM, Stable Diffusion) will be too
  slow for interactive use and may time out.
- If you need GPU inference, the platform would need to move to a GPU-enabled
  host (Modal, Replicate, or a GPU Lightsail instance at ~$40+/month).

### Frame rate — 10 FPS target, 300 frame cap

The platform skips frames from the source video to target approximately
10 processed frames per second of source footage. It also caps output at
300 frames total (~30 seconds of source at 10 FPS).

**What this means for your project:**
- Your function will not be called for every frame in the source video.
- Do not rely on frame-to-frame continuity for stateful algorithms
  (tracking, optical flow) — the skipped frames will break the temporal chain.
- If your algorithm requires every frame (e.g. you're counting events over
  time), this platform is not the right showcase for it. Consider pre-processing
  the video offline and displaying the result instead.

### File size — 50MB maximum

Uploads are capped at 50MB. This is enforced both for memory safety and
to prevent abuse on the public-facing server.

**What this means for your project:**
- Short demo clips (5-15 seconds, 720p, h264) are ideal.
- Images work at any reasonable resolution — a 4K PNG is typically under 50MB.
- Provide sample files in `backend/app/cv_projects/samples/` so recruiters
  can test without needing their own files.

### Processing time — synchronous, no background jobs

`process_frame` is called synchronously on the server. There is no job queue
or background worker. If your function takes more than ~2 seconds per frame,
the streaming response will appear very slow to the user.

**Guideline:** Keep per-frame processing under 500ms on CPU for a usable
demo experience.

### Output must be a visual frame

The platform displays your output as an image in the browser. It cannot
display structured data (JSON, text, audio) directly. If your CV project
produces structured output (e.g. bounding box coordinates, dice counts),
**draw the results onto the frame** before returning:

```python
# Draw text overlay
cv2.putText(frame, f"Count: {count}", (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

# Draw bounding boxes
cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

return frame
```

---

## Example: Minimal Integration

Here is the complete integration for a simple project that inverts colors,
as a reference template:

```python
# backend/app/cv_projects/invert.py
import numpy as np

def process_frame(frame: np.ndarray) -> np.ndarray:
    """Invert all pixel values."""
    return 255 - frame
```

```python
# backend/app/processors.py (additions only)
from .cv_projects.invert import process_frame as invert_fn

PROCESSORS = {
    # ... existing ...
    "invert": invert_fn,
}

PROCESSOR_META = [
    # ... existing ...
    {
        "id": "invert",
        "label": "Color Invert",
        "description": "Inverts all pixel values, producing a negative of the image.",
    },
]
```

Rebuild with `docker compose up --build`, and the new filter appears in the
dropdown immediately.

---

## Checklist

Before integrating a new CV project:

- [ ] Function accepts BGR `np.ndarray`, returns BGR `np.ndarray` (H, W, 3), uint8
- [ ] Model weights (if any) loaded at module level, not inside `process_frame`
- [ ] Model weights fit within ~200MB
- [ ] Per-frame processing is under ~500ms on CPU
- [ ] Results are drawn onto the frame (not returned as separate data)
- [ ] No unhandled exceptions — failures return a fallback frame
- [ ] Entry added to both `PROCESSORS` and `PROCESSOR_META` in `processors.py`
- [ ] Tested locally with `docker compose up --build`
- [ ] Sample input file added to `backend/app/cv_projects/samples/` (optional but helpful)
