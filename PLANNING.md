kiro-cli --resume-id 3d1ba314-8b81-401a-92b9-9b3079784b38

# CV Showcase - Planning Document

This project is intended to be used as a sort of "hub" to showcase my past and future Computer Vision (CV) projects (at least ones that are focused on the CV part itself rather than parts built off of it) such that recruiters and people curious of my work can access and observe my work.

---

## FUNCTIONALITY REQUIREMENTS
- Should be able to store sample images and videos to be able to run CV projects on
- Should be able to upload images and videos to be able to run CV projects on (does not need to keep these files)
- Should be able to access webcam to be able to run CV projects on (should NOT be recording if not necessary)
- Should be able to switch between different CV projects
- For each CV operation, should have section that describes the CV project
- Should have pre-CV and post-CV screen to show original (for CV projects that directly manipulate the source)
- Should be able to be hosted on a website, so as to be accessible by recruiters and people curious of my work

## POTENTIAL SAMPLE LAYOUT

```
Dropdown Menu 1 - Selects CV Project/Configuration
Dropdown Menu 2 - Selects Source

Box 1 - Original Source
Box 2 - Altered Source

Paragraph - About section for CV Project
```

---

## FINALIZED ARCHITECTURE

```
Recruiter's Browser
       ↓
[Cloudflare Pages] → Serves static HTML/JS/CSS (free)
       ↓ (HTTP Streaming)
[AWS Lightsail $3.50/mo] → FastAPI backend running CV code
```

### Tech Stack
- **Backend:** FastAPI (async), OpenCV, Pillow, NumPy, Docker
- **Frontend:** React + TypeScript
- **Video Streaming:** HTTP chunked streaming (server-sent events pattern)
- **Frontend Hosting:** Cloudflare Pages (free)
- **Backend Hosting:** AWS Lightsail $3.50/month (512MB RAM, 2 vCPU shared, 20GB SSD, 1TB transfer)
- **Development:** Docker Compose for local environment

### Key Design Decisions
- **Video-first approach:** Stream processed frames back to frontend as they are ready
- **Server-side inference:** Run actual Python/OpenCV code unchanged on the backend
- **No persistence:** Stateless — no user accounts, no stored uploads
- **Docker from day one:** Consistent environment across local → AWS Lightsail
- **Webcam:** Planned for ~1-2 months after initial launch; not in initial scope
- **CV implementations:** Done separately per-project; platform uses placeholder CV filters (grayscale, edge detection, blur) until real projects are integrated

### Security Considerations
- Validate file uploads by magic bytes (not just extension)
- Cap file size at 50MB (also required for 512MB RAM constraint)
- Process uploads in memory/temp directory, discard immediately
- Rate-limit API endpoints
- HTTPS only (Cloudflare handles frontend TLS, Lightsail configured for backend)
- CORS restricted to frontend domain only

---

## COST ANALYSIS

| Component | Monthly | Annual | Notes |
|-----------|---------|--------|-------|
| AWS Lightsail | $3.50 | $42 | Backend, always-on |
| Cloudflare Pages | $0 | $0 | Frontend CDN |
| Domain (optional) | ~$1 | ~$12 | Namecheap/Cloudflare |
| **Total** | **~$4.50** | **~$54** | |

Upgrade path if more RAM needed: $3.50 → $5 (1GB) → $10 (2GB) → $20 (4GB)

---

## IMPLEMENTATION PLAN

### Task 1: Project Foundation & Docker Setup
- Initialize Git repository
- Create Docker Compose with backend (FastAPI) and frontend (React) services
- Setup basic project structure
- Configure backend CORS to allow frontend access
- **Done when:** Docker containers running, backend `/health` responds, frontend shows "Hello World"

### Task 2: Basic Video Processing Pipeline
- Implement FastAPI endpoint that accepts video uploads
- Create placeholder CV processors (grayscale, edge detection, blur)
- Implement HTTP streaming response with processed frames
- Test with a sample video file
- **Done when:** Upload video → streaming processed frames appear in browser

### Task 3: Frontend Polish & UX
- Add loading states and progress indicators
- Implement generic error handling ("something went wrong")
- Add dropdown with placeholder CV projects
- Add project descriptions/help text
- Style side-by-side original vs processed video displays
- **Done when:** Polished UI with placeholder CV projects working and proper error states

### Task 4: Deployment Infrastructure (AWS Lightsail)
- Create AWS account / provision Lightsail $3.50 instance
- Deploy Docker containers to Lightsail
- Setup Cloudflare Pages for frontend
- Configure DNS and HTTPS
- Enable swap file (1GB) to compensate for 512MB RAM
- **Done when:** Live website accessible publicly at a real URL

### Task 5: Webcam Integration (~1-2 months post-launch)
- Add react-webcam component
- Implement HTTP streaming for webcam frames
- Modify backend to handle real-time webcam streams
- Add toggle between file upload and webcam
- **Done when:** Webcam processed in real-time with placeholder CV filters

### Task 6: Performance Optimization & Monitoring
- Add request rate limiting
- Implement frame rate control (10 FPS max for 512MB constraint)
- Add Lightsail monitoring alerts
- Setup memory usage guards
- **Done when:** Platform stable under single-user load with memory safeguards

---

## CV PROJECTS ROADMAP (Separate Repos, Integrated Here)
- **Dice Counter:** Traditional CV methods (contour detection, dot counting)
- **Blueprintifier:** Edge detection + color manipulation to create blueprint effect
- More TBD

### Integration Pattern
Each CV project exposes a standard processor interface:
```python
def process_frame(frame: np.ndarray) -> np.ndarray:
    # CV algorithm here
    return processed_frame
```
New projects are added by dropping a processor into the backend and updating a config file.

---

## OPEN QUESTIONS / FUTURE DECISIONS
- Domain name selection
- Whether to support mobile (likely graceful degradation)
- Analytics strategy (anonymized, GDPR-compliant)
- Long-term: GPU upgrade path if heavier models needed (~3 months)
