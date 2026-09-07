import io
import json
import zipfile
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, LargeBinary, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import PyPDF2
from openai import OpenAI

from app.config import settings

# Import the Candidate model from the main app
from app.models.entities import Candidate

# -------------------------------------------------------------------
# Database Setup (Isolated from the main app)
# -------------------------------------------------------------------
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
ResumeBase = declarative_base()

class UploadedResume(ResumeBase):
    __tablename__ = "uploaded_resumes"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), index=True)
    content_type = Column(String(100))
    file_data = Column(LargeBinary)
    extracted_text = Column(Text, nullable=True)
    parsed_data = Column(JSON, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

# Create the tables for this standalone API
ResumeBase.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------------------------------------------------
# AI Configuration
# -------------------------------------------------------------------
openai_client = OpenAI(base_url=settings.explabs_base_url, api_key=settings.explabs_api_key)

def extract_resume_details(text: str) -> dict:
    if not text or not text.strip():
        return {}
    
    prompt = f"""You are an expert recruiter AI. Extract the following details from the resume text below:
- Name
- Email
- Phone
- Location
- Experience Years (as a number)
- Current Company
- Current Title
- Skills (as a list of strings)

Return ONLY a valid JSON object matching this schema:
{{
  "name": "string or null",
  "email": "string or null",
  "phone": "string or null",
  "location": "string or null",
  "experience_years": 0.0,
  "current_company": "string or null",
  "current_title": "string or null",
  "skills": ["string", "string"]
}}

RESUME TEXT:
{text[:4000]}"""
    try:
        r = openai_client.chat.completions.create(
            model=settings.explabs_model,
            messages=[{"role":"user","content":prompt}],
        )
        content = r.choices[0].message.content or "{}"
        
        # Clean markdown formatting if present
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
            
        return json.loads(content)
    except Exception as e:
        print(f"Failed to extract AI details: {e}")
        return {}

# -------------------------------------------------------------------
# FastAPI App
# -------------------------------------------------------------------
app = FastAPI(title="Standalone Resume Ingestion API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
    except Exception as e:
        print(f"Failed to extract PDF text: {e}")
        return ""

def process_file(filename: str, content: bytes, content_type: str, db: Session):
    extracted_text = None
    parsed_data = None
    
    # Simple text extraction for PDFs
    if filename.lower().endswith('.pdf'):
        extracted_text = extract_text_from_pdf(content)
        if extracted_text:
            parsed_data = extract_resume_details(extracted_text)
            
            # Save the candidate details directly to the main Candidate table
            if parsed_data and parsed_data.get("name"):
                skills_list = parsed_data.get("skills") or []
                new_candidate = Candidate(
                    name=parsed_data.get("name") or "Unknown Candidate",
                    email=parsed_data.get("email"),
                    phone=parsed_data.get("phone") or "N/A",  # Phone is required by DB schema
                    location=parsed_data.get("location"),
                    experience_years=float(parsed_data.get("experience_years") or 0.0),
                    current_company=parsed_data.get("current_company"),
                    current_title=parsed_data.get("current_title"),
                    skills=", ".join(skills_list)
                )
                db.add(new_candidate)
        
    resume = UploadedResume(
        filename=filename,
        content_type=content_type,
        file_data=content,
        extracted_text=extracted_text,
        parsed_data=parsed_data
    )
    db.add(resume)
    return resume

@app.post("/api/resumes/upload")
async def upload_resumes(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    """
    Upload one or more resumes, or a ZIP file containing resumes.
    Files will be stored in the database as binary data, and text will be extracted for PDFs.
    """
    processed_count = 0
    saved_filenames = []

    for file in files:
        content = await file.read()
        
        # Handle ZIP files
        if file.filename.lower().endswith('.zip'):
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    for zip_info in z.infolist():
                        if zip_info.is_dir() or zip_info.filename.startswith('__MACOSX'):
                            continue
                            
                        # Read individual file from zip
                        with z.open(zip_info) as f:
                            zip_file_content = f.read()
                            
                        # Guess content type based on extension
                        c_type = "application/pdf" if zip_info.filename.lower().endswith('.pdf') else "application/octet-stream"
                        
                        process_file(zip_info.filename, zip_file_content, c_type, db)
                        processed_count += 1
                        saved_filenames.append(zip_info.filename)
            except zipfile.BadZipFile:
                raise HTTPException(status_code=400, detail=f"Invalid ZIP file: {file.filename}")
        else:
            # Handle standard files (PDF, DOCX, etc.)
            process_file(file.filename, content, file.content_type, db)
            processed_count += 1
            saved_filenames.append(file.filename)
            
    db.commit()
    
    return {
        "message": f"Successfully processed {processed_count} file(s).",
        "saved_files": saved_filenames
    }

@app.get("/api/resumes")
def list_resumes(db: Session = Depends(get_db)):
    """
    List all uploaded resumes (excluding the raw binary data to save bandwidth).
    """
    resumes = db.query(
        UploadedResume.id, 
        UploadedResume.filename, 
        UploadedResume.content_type, 
        UploadedResume.uploaded_at,
        UploadedResume.parsed_data
    ).order_by(UploadedResume.uploaded_at.desc()).all()
    
    return [
        {
            "id": r.id, 
            "filename": r.filename, 
            "content_type": r.content_type, 
            "uploaded_at": r.uploaded_at,
            "parsed_data": r.parsed_data
        } for r in resumes
    ]

# Entry point for running locally via python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("resume_api:app", host="0.0.0.0", port=8001, reload=True)
