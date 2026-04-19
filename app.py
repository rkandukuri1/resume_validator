from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List
from openai import OpenAI
from dotenv import load_dotenv
from docx import Document
import os

# -----------------------------
# Load API Key
# -----------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -----------------------------
# Create App
# -----------------------------
app = FastAPI(title="Resume Validator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Models
# -----------------------------
class ResumeValidator(BaseModel):
    match_score: int = Field(ge=0, le=100)
    matched_skills: List[str]
    missing_skills: List[str]
    experience_match: str
    strengths: List[str]
    suggestions: List[str]
    final_resolution: str


class ImprovedResume(BaseModel):
    improved_resume: str


class ResumeRequest(BaseModel):
    resume_text: str
    requirement_text: str


class ImproveRequest(BaseModel):
    resume_text: str
    requirement_text: str
    missing_skills: List[str]


# -----------------------------
# Validate Resume
# -----------------------------
def process_resume(resume_docs, req_docs):
    prompt = f"""
Validate the resume against the requirement.

RESUME:
{resume_docs}

REQUIREMENT:
{req_docs}
"""

    response = client.beta.chat.completions.parse(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4.1-nano",
        response_format=ResumeValidator
    )

    return response.choices[0].message.parsed


# -----------------------------
# Improve Resume
# -----------------------------
def generate_improved_resume(resume_text, req_text, missing_skills):
    prompt = f"""
Improve this resume for the job.

Missing Skills:
{missing_skills}

REQUIREMENT:
{req_text}

RESUME:
{resume_text}
"""

    response = client.beta.chat.completions.parse(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4.1",
        response_format=ImprovedResume
    )

    return response.choices[0].message.parsed


# -----------------------------
# Create Word file
# -----------------------------
def create_resume_file(text):
    doc = Document()

    for line in text.split("\n"):
        doc.add_paragraph(line)

    file_path = "improved_resume.docx"
    doc.save(file_path)

    return file_path


# -----------------------------
# API - Validate
# -----------------------------
@app.post("/validate-resume", response_model=ResumeValidator)
def validate_resume(data: ResumeRequest):
    return process_resume(data.resume_text, data.requirement_text)


# -----------------------------
# API - Improve + Download
# -----------------------------
@app.post("/generate-improved-resume")
def improve_resume(data: ImproveRequest):
    improved = generate_improved_resume(
        data.resume_text,
        data.requirement_text,
        data.missing_skills
    )

    file_path = create_resume_file(improved.improved_resume)

    return FileResponse(
        path=file_path,
        filename="improved_resume.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )