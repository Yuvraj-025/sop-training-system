import os
import uuid
import logging
import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INGESTION_URL    = os.getenv("INGESTION_URL",    "http://ingestion:8001")
AI_PROCESSOR_URL = os.getenv("AI_PROCESSOR_URL", "http://ai-processor:8002")
PRESENTATION_URL = os.getenv("PRESENTATION_URL", "http://presentation:8003")
STORAGE_URL      = os.getenv("STORAGE_URL",      "http://storage:8004")

TIMEOUT = httpx.Timeout(120.0, connect=10.0)

app = FastAPI(
    title="SOP Training System — API Gateway",
    description="Central gateway that orchestrates all SOP training microservices",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ────────────────────────────────────────────────────────────
# HEALTH
# ────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    services = {
        "ingestion":    f"{INGESTION_URL}/health",
        "ai-processor": f"{AI_PROCESSOR_URL}/health",
        "presentation": f"{PRESENTATION_URL}/health",
        "storage":      f"{STORAGE_URL}/health",
    }
    results = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in services.items():
            try:
                r = await client.get(url)
                results[name] = r.json()
            except Exception as e:
                results[name] = {"status": "unreachable", "error": str(e)}
    all_healthy = all(v.get("status") == "healthy" for v in results.values())
    return {"gateway": "healthy", "services": results, "all_healthy": all_healthy}


# ────────────────────────────────────────────────────────────
# UPLOAD — Ingestion only
# ────────────────────────────────────────────────────────────
@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    """Upload SOP document → extract text via Ingestion Service."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            files = {"file": (file.filename, await file.read(), file.content_type)}
            r = await client.post(f"{INGESTION_URL}/upload", files=files)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ingestion service error: {str(e)}")


# ────────────────────────────────────────────────────────────
# PROCESS — Full AI pipeline
# ────────────────────────────────────────────────────────────
class ProcessRequest(BaseModel):
    text: str
    filename: Optional[str] = "SOP Document"


@app.post("/api/process")
async def process(req: ProcessRequest):
    """Run SOP text through AI processor and save to storage."""
    job_id = str(uuid.uuid4())

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # 1. Call AI processor
        try:
            ai_resp = await client.post(
                f"{AI_PROCESSOR_URL}/process-all",
                json={"text": req.text},
            )
            ai_resp.raise_for_status()
            ai_output = ai_resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code,
                                detail=f"AI Processor: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI Processor error: {str(e)}")

        # 2. Save to storage
        try:
            save_resp = await client.post(
                f"{STORAGE_URL}/save",
                json={
                    "job_id": job_id,
                    "filename": req.filename,
                    "sop_text": req.text,
                    "ai_output": ai_output,
                },
            )
            save_resp.raise_for_status()
        except Exception as e:
            logger.warning(f"Storage save failed (non-fatal): {e}")

    return {
        "job_id": job_id,
        "filename": req.filename,
        **ai_output,
    }


# ────────────────────────────────────────────────────────────
# PRESENTATION — Generate PPTX
# ────────────────────────────────────────────────────────────
class PresentationRequest(BaseModel):
    summary: dict
    training: dict
    quiz: dict
    job_id: str
    filename: Optional[str] = "SOP_Training"


@app.post("/api/presentation")
async def create_presentation(req: PresentationRequest):
    """Ask Presentation Service to build a PPTX and update storage."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            p_resp = await client.post(
                f"{PRESENTATION_URL}/generate",
                json={
                    "summary": req.summary,
                    "training": req.training,
                    "quiz": req.quiz,
                    "filename": req.filename,
                },
            )
            p_resp.raise_for_status()
            pptx_data = p_resp.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code,
                                detail=f"Presentation Service: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Presentation error: {str(e)}")

        # Update storage with pptx job id
        try:
            job = await client.get(f"{STORAGE_URL}/jobs/{req.job_id}")
            if job.status_code == 200:
                job_data = job.json()
                await client.post(f"{STORAGE_URL}/save", json={
                    "job_id": f"{req.job_id}_pptx_update",
                    "filename": req.filename,
                    "sop_text": "",
                    "ai_output": {},
                    "pptx_job_id": pptx_data.get("job_id"),
                })
        except Exception:
            pass

    pptx_data["presentation_download_url"] = (
        f"{PRESENTATION_URL}/download/{pptx_data['job_id']}"
    )
    return pptx_data


# ────────────────────────────────────────────────────────────
# JOBS history
# ────────────────────────────────────────────────────────────
@app.get("/api/jobs")
async def get_jobs():
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{STORAGE_URL}/jobs")
        r.raise_for_status()
        return r.json()


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{STORAGE_URL}/jobs/{job_id}")
        if r.status_code == 404:
            raise HTTPException(status_code=404, detail="Job not found")
        r.raise_for_status()
        return r.json()
