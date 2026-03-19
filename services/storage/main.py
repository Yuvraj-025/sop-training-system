import os
import json
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:////app/data/sop_storage.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


class SOPJob(Base):
    __tablename__ = "sop_jobs"
    id         = Column(Integer, primary_key=True, index=True)
    job_id     = Column(String, unique=True, index=True)
    filename   = Column(String)
    sop_text   = Column(Text)
    ai_output  = Column(Text)   # JSON string
    pptx_job_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


app = FastAPI(
    title="SOP Storage Service",
    description="Persists SOP processing jobs and results using SQLite",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created / verified")


class SaveJobRequest(BaseModel):
    job_id: str
    filename: str
    sop_text: str
    ai_output: dict
    pptx_job_id: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "storage"}


@app.post("/save")
async def save_job(req: SaveJobRequest):
    async with AsyncSessionLocal() as session:
        job = SOPJob(
            job_id=req.job_id,
            filename=req.filename,
            sop_text=req.sop_text,
            ai_output=json.dumps(req.ai_output),
            pptx_job_id=req.pptx_job_id,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
    logger.info(f"Saved job {req.job_id}")
    return {"id": job.id, "job_id": job.job_id, "created_at": str(job.created_at)}


@app.get("/jobs")
async def list_jobs():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SOPJob).order_by(SOPJob.id.desc()).limit(50))
        jobs = result.scalars().all()
    return [
        {
            "id": j.id,
            "job_id": j.job_id,
            "filename": j.filename,
            "word_count": len(j.sop_text.split()) if j.sop_text else 0,
            "pptx_job_id": j.pptx_job_id,
            "created_at": str(j.created_at),
        }
        for j in jobs
    ]


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SOPJob).where(SOPJob.job_id == job_id))
        job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "job_id": job.job_id,
        "filename": job.filename,
        "sop_text": job.sop_text,
        "ai_output": json.loads(job.ai_output),
        "pptx_job_id": job.pptx_job_id,
        "created_at": str(job.created_at),
    }
