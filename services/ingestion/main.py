from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import io
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SOP Ingestion Service",
    description="Handles SOP document uploads and text extraction",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ingestion"}


@app.post("/upload")
async def upload_sop(file: UploadFile = File(...)):
    """
    Accept a PDF or plain-text SOP file and return extracted text.
    """
    filename = file.filename or "unknown"
    content_type = file.content_type or ""

    logger.info(f"Received file: {filename} ({content_type})")

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # ── PDF extraction ──────────────────────────────────────────────
    if filename.lower().endswith(".pdf") or "pdf" in content_type:
        try:
            extracted_pages = []
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        extracted_pages.append(text.strip())
            full_text = "\n\n".join(extracted_pages)
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise HTTPException(status_code=422, detail=f"PDF parsing failed: {str(e)}")

    # ── Plain text ──────────────────────────────────────────────────
    elif filename.lower().endswith(".txt") or "text" in content_type:
        try:
            full_text = file_bytes.decode("utf-8", errors="ignore")
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Text decoding failed: {str(e)}")

    else:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Please upload a .pdf or .txt file.",
        )

    full_text = full_text.strip()
    if not full_text:
        raise HTTPException(
            status_code=422, detail="Could not extract any text from the document."
        )

    word_count = len(full_text.split())
    logger.info(f"Extracted {word_count} words from {filename}")

    return {
        "filename": filename,
        "text": full_text,
        "word_count": word_count,
        "pages": len(extracted_pages) if filename.lower().endswith(".pdf") else 1,
    }
