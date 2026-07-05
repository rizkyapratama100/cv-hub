from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from .routers import video

app = FastAPI(title="CV Showcase API", version="0.1.0")

# CORS — restrict to frontend origin in production via ALLOWED_ORIGINS env var
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(video.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "cv-showcase-backend"}
