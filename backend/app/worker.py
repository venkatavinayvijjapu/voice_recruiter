from celery import Celery
from sqlalchemy import select
from .config import settings
from .db import SessionLocal
from .models import Screening, Job, Candidate
from .services.hunar import HunarClient
from .services.astra import evaluate_screening

celery_app = Celery("hiring", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(task_track_started=True, timezone="Asia/Kolkata")
TERMINAL = {"COMPLETED", "NOT_CONNECTED", "FAILED", "CANCELLED", "NO_ANSWER"}

@celery_app.task(bind=True, max_retries=3)
def poll_screening(self, screening_id: int):
    db = SessionLocal()
    try:
        s = db.get(Screening, screening_id)
        if not s or not s.hunar_call_id: return
        data = HunarClient().get_call(s.hunar_call_id)
        provider_status = data.get("status") or "UNKNOWN"
        lifecycle_status = data.get("lifecycle_status") or provider_status
        status = lifecycle_status
        if data.get("result") and (data.get("ended_at") or data.get("recording_url")):
            status = "COMPLETED"
        s.status = status
        s.lifecycle_status = lifecycle_status
        s.raw_call = data
        s.recording_url = data.get("recording_url")
        s.transcript = data.get("transcript") or data.get("transcription")
        db.commit()
        if status not in TERMINAL:
            poll_screening.apply_async(args=[screening_id], countdown=60)
            return
        if status == "COMPLETED" and not s.evaluation:
            job = db.get(Job, s.job_id)
            candidate = db.get(Candidate, s.candidate_id)
            evaluation = evaluate_screening(job.description, {
                "name": candidate.name, "experience_years": candidate.experience_years,
                "location": candidate.location, "current_company": candidate.current_company,
                "current_title": candidate.current_title, "skills": candidate.skills,
            }, data)
            s.evaluation = evaluation
            s.status = "EVALUATED"
            db.commit()
    except Exception as exc:
        db.rollback()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30)
        s = db.get(Screening, screening_id)
        if s:
            s.error = str(exc); db.commit()
    finally:
        db.close()
