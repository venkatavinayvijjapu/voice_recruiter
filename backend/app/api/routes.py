import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Job, Candidate, Screening
from ..services.astra import parse_jd, generate_questions
from ..services.hunar import HunarClient
from ..worker import poll_screening

router = APIRouter(prefix="/api")

class JobCreate(BaseModel):
    title: str | None = None
    description: str = Field(min_length=20)

class ScreeningStart(BaseModel):
    candidate_ids: list[int] = Field(min_length=1)

class ScreeningDecision(BaseModel):
    decision: str

@router.get("/health")
def health(): return {"status":"ok"}

@router.post("/jobs")
def create_job(body: JobCreate, db: Session = Depends(get_db)):
    req = parse_jd(body.description)
    questions = generate_questions(body.description, req)
    job = Job(title=body.title or req.get("role") or "Untitled role", description=body.description, requirements=req, questions=questions)
    db.add(job); db.commit(); db.refresh(job)
    return {"id":job.id,"title":job.title,"requirements":req,"questions":questions}

@router.get("/jobs")
def jobs(db: Session = Depends(get_db)):
    return [{"id":j.id,"title":j.title,"created_at":j.created_at} for j in db.scalars(select(Job).order_by(Job.id.desc())).all()]

@router.get("/jobs/{job_id}/candidates")
def candidates(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job: raise HTTPException(404,"Job not found")
    req = job.requirements or {}; skills = [s.lower() for s in req.get("required_skills", [])]
    minexp = float(req.get("min_experience_years") or 0); location = (req.get("location") or "").strip().lower()
    rows=[]
    for c in db.scalars(select(Candidate)).all():
        text=(c.skills or "").lower()
        if c.experience_years < minexp: continue
        if location and (c.location or "").strip().lower() != location: continue
        if any(skill not in text for skill in skills): continue
        rows.append({"id":c.candidate_id,"name":c.name,"email":c.email,"phone":c.phone,"location":c.location,"experience_years":c.experience_years,"current_company":c.current_company,"current_title":c.current_title,"skills":c.skills})
    return rows

@router.post("/jobs/{job_id}/screenings")
def start_screening(job_id: int, body: ScreeningStart, db: Session = Depends(get_db)):
    job=db.get(Job,job_id)
    if not job: raise HTTPException(404,"Job not found")
    candidates=[db.get(Candidate,cid) for cid in body.candidate_ids]
    if any(c is None for c in candidates): raise HTTPException(400,"Candidate not found")
    phone_owners = {}
    for c in candidates:
        phone_key = "".join(ch for ch in (c.phone or "") if ch.isdigit())[-10:]
        if phone_key and phone_key in phone_owners:
            raise HTTPException(400, f"Candidates {phone_owners[phone_key]} and {c.name} share the same phone number. Update one number before starting calls.")
        phone_owners[phone_key] = c.name
    rows=[]; screenings=[]
    for c in candidates:
        screenings.append(Screening(job_id=job_id,candidate_id=c.candidate_id,status="CREATING"))
        rows.append({"callee_name":c.name,"mobile_number":c.phone,"custom_data":{"job_role":job.requirements.get("role",job.title),"job_description":job.description,"candidate_experience":str(c.experience_years),"candidate_location":c.location or "","interview_questions":"\n".join(f"{i+1}. {q}" for i,q in enumerate(job.questions))}})
    if not rows: return {"created":0,"calls":[]}
    try: calls=HunarClient().create_bulk(rows, f"job-{job_id}-{uuid.uuid4()}")
    except Exception as e:
        for s in screenings: s.status="FAILED"; s.error=str(e); db.add(s)
        db.commit(); raise HTTPException(502,f"Hunar call creation failed: {e}")
    for s,call in zip(screenings,calls):
        s.hunar_call_id = call.get("id")
        s.status = call.get("status") or "NOT_STARTED"
        db.add(s)
    db.commit()
    for s in screenings:
        try:
            poll_screening.apply_async(args=[s.id], countdown=30)
        except Exception as exc:
            s.error = f"Status polling could not be queued: {exc}"
    db.commit()
    return {"created":len(screenings),"calls":[{"screening_id":s.id,"candidate_id":s.candidate_id,"call_id":s.hunar_call_id,"status":s.status} for s in screenings]}

@router.get("/jobs/{job_id}/screenings")
def screenings(job_id:int, db:Session=Depends(get_db)):
    stmt = select(Screening, Candidate).join(
        Candidate,
        Candidate.candidate_id == Screening.candidate_id
    ).where(
        Screening.job_id == job_id
    ).order_by(Screening.id.desc())
    out=[]
    for s,c in db.execute(stmt).all(): out.append({"id":s.id,"candidate":{"id":c.candidate_id,"name":c.name,"email":c.email,"phone":c.phone},"status":s.status,"lifecycle_status":s.lifecycle_status,"redial_status":(s.raw_call or {}).get("redial_status"),"duration_seconds":(s.raw_call or {}).get("duration_seconds"),"provider_result":(s.raw_call or {}).get("result") or {},"recording_url":s.recording_url,"transcript":s.transcript,"evaluation":s.evaluation,"recruiter_decision":(s.evaluation or {}).get("recruiter_decision"),"error":s.error})
    return out

@router.post("/screenings/{screening_id}/decision")
def update_screening_decision(screening_id:int, body: ScreeningDecision, db:Session=Depends(get_db)):
    s=db.get(Screening, screening_id)
    if not s: raise HTTPException(404,"Screening not found")
    decision = body.decision.strip().upper()
    if decision not in {"SHORTLIST", "HOLD", "REJECT"}:
        raise HTTPException(400, "Decision must be one of SHORTLIST, HOLD, or REJECT")
    evaluation = dict(s.evaluation or {})
    evaluation["recruiter_decision"] = decision
    s.evaluation = evaluation
    db.add(s); db.commit(); db.refresh(s)
    return {"id": s.id, "recruiter_decision": decision, "evaluation": s.evaluation}

@router.get("/screenings/{screening_id}")
def screening(screening_id:int, db:Session=Depends(get_db)):
    s=db.get(Screening,screening_id)
    if not s: raise HTTPException(404,"Screening not found")
    c=db.get(Candidate,s.candidate_id); j=db.get(Job,s.job_id)
    return {"id":s.id,"job":{"id":j.id,"title":j.title},"candidate":{"id":c.candidate_id,"name":c.name,"email":c.email,"phone":c.phone,"location":c.location,"experience_years":c.experience_years,"current_company":c.current_company,"current_title":c.current_title,"skills":c.skills},"status":s.status,"lifecycle_status":s.lifecycle_status,"raw_call":s.raw_call,"recording_url":s.recording_url,"transcript":s.transcript,"evaluation":s.evaluation,"recruiter_decision":(s.evaluation or {}).get("recruiter_decision"),"error":s.error}
