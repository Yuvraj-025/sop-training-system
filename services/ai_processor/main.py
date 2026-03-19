import os
import json
import logging
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

MODEL_NAME = "gemini-2.5-flash"

app = FastAPI(
    title="SOP AI Processing Service",
    description="Uses Google Gemini to generate summaries, training content, and quiz questions from SOP text",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SOPText(BaseModel):
    text: str


def get_client():
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY is not configured. Please set it in your .env file.",
        )
    return genai.Client(api_key=GEMINI_API_KEY)


def generate(prompt: str) -> str:
    client = get_client()
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    return response.text


def extract_json(raw: str) -> dict:
    """Strip markdown code fences and parse JSON."""
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}\nRaw response: {raw[:500]}")
        raise HTTPException(status_code=502, detail=f"AI returned invalid JSON: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ai-processor", "model": MODEL_NAME, "api_key_set": bool(GEMINI_API_KEY)}


@app.post("/summarize")
async def summarize(body: SOPText):
    """Generate a structured summary of the SOP."""
    prompt = f"""
You are an expert SOP analyst. Analyze the following SOP document and return a structured JSON summary.

Return ONLY a valid JSON object (no markdown, no code fences) with this exact structure:
{{
  "title": "Document title inferred from content",
  "overview": "2-3 sentence overview of what this SOP covers",
  "department": "Department or team this SOP applies to",
  "purpose": "The primary purpose of this SOP",
  "scope": "Who this SOP applies to",
  "key_points": ["key point 1", "key point 2", "key point 3", "...up to 8 points"],
  "sections": [
    {{
      "heading": "Section name",
      "summary": "Brief summary of this section"
    }}
  ],
  "compliance_notes": "Any compliance, safety, or regulatory notes"
}}

SOP DOCUMENT:
{body.text[:6000]}
"""
    return extract_json(generate(prompt))


@app.post("/training")
async def training_content(body: SOPText):
    """Generate step-by-step training content from the SOP."""
    prompt = f"""
You are an expert employee trainer. Convert the following SOP into structured training modules for new employees.

Return ONLY a valid JSON object (no markdown, no code fences) with this exact structure:
{{
  "training_title": "Training program title",
  "target_audience": "Who this training is for",
  "estimated_duration": "Estimated time to complete (e.g., '45 minutes')",
  "learning_objectives": ["objective 1", "objective 2", "objective 3"],
  "modules": [
    {{
      "module_number": 1,
      "title": "Module title",
      "objective": "What the trainee will learn",
      "steps": [
        {{
          "step_number": 1,
          "action": "What to do",
          "details": "How to do it with specifics",
          "responsible": "Who is responsible"
        }}
      ],
      "tips": ["Helpful tip or best practice"],
      "common_mistakes": ["Common mistake to avoid"]
    }}
  ],
  "summary": "Overall training summary and next steps"
}}

SOP DOCUMENT:
{body.text[:6000]}
"""
    return extract_json(generate(prompt))


@app.post("/quiz")
async def generate_quiz(body: SOPText):
    """Generate 5 evaluation quiz questions based on the SOP."""
    prompt = f"""
You are an expert instructional designer. Create exactly 5 multiple-choice quiz questions to evaluate employee understanding of the following SOP.

Return ONLY a valid JSON object (no markdown, no code fences) with this exact structure:
{{
  "quiz_title": "Quiz title based on SOP content",
  "instructions": "Instructions for the quiz taker",
  "time_limit": "Suggested time limit (e.g., '10 minutes')",
  "passing_score": "Passing percentage (e.g., '80%')",
  "questions": [
    {{
      "question_number": 1,
      "question": "Clear, specific question about the SOP",
      "options": {{
        "A": "Option A text",
        "B": "Option B text",
        "C": "Option C text",
        "D": "Option D text"
      }},
      "correct_answer": "A",
      "explanation": "Why this answer is correct and others are wrong",
      "difficulty": "easy|medium|hard",
      "topic": "What SOP section this tests"
    }}
  ]
}}

SOP DOCUMENT:
{body.text[:6000]}
"""
    return extract_json(generate(prompt))


@app.post("/process-all")
async def process_all(body: SOPText):
    """Generate summary, training content, and quiz in a single call."""
    logger.info(f"Processing SOP with {len(body.text.split())} words")

    prompt = f"""
You are an expert SOP analyst and trainer. Analyze the following SOP and return a comprehensive training package.

Return ONLY a valid JSON object (no markdown, no code fences) with this EXACT structure:
{{
  "summary": {{
    "title": "...",
    "overview": "...",
    "department": "...",
    "purpose": "...",
    "scope": "...",
    "key_points": ["...", "..."],
    "sections": [{{"heading": "...", "summary": "..."}}],
    "compliance_notes": "..."
  }},
  "training": {{
    "training_title": "...",
    "target_audience": "...",
    "estimated_duration": "...",
    "learning_objectives": ["...", "..."],
    "modules": [
      {{
        "module_number": 1,
        "title": "...",
        "objective": "...",
        "steps": [{{"step_number": 1, "action": "...", "details": "...", "responsible": "..."}}],
        "tips": ["..."],
        "common_mistakes": ["..."]
      }}
    ],
    "summary": "..."
  }},
  "quiz": {{
    "quiz_title": "...",
    "instructions": "...",
    "time_limit": "...",
    "passing_score": "...",
    "questions": [
      {{
        "question_number": 1,
        "question": "...",
        "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
        "correct_answer": "A",
        "explanation": "...",
        "difficulty": "medium",
        "topic": "..."
      }}
    ]
  }}
}}

Generate at least 3 training modules and exactly 5 quiz questions.

SOP DOCUMENT:
{body.text[:7000]}
"""
    result = extract_json(generate(prompt))
    logger.info("Successfully generated complete training package")
    return result
