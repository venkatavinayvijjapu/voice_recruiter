import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal, Base, engine
from app.models import Job, Candidate, Screening


class ScreeningDecisionFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)

    def test_screening_decision_persists_and_is_exposed(self):
        db = SessionLocal()
        try:
            job = Job(
                title='Engineer',
                description='Need backend engineer with Python and SQL',
                requirements={'role': 'Engineer', 'required_skills': ['python'], 'min_experience_years': 2, 'location': 'Bengaluru'},
                questions=['Q1']
            )
            candidate = Candidate(name='Amit', phone='9999999999', experience_years=3, location='Bengaluru', skills='Python, SQL')
            db.add_all([job, candidate])
            db.commit()
            db.refresh(job)
            db.refresh(candidate)

            screening = Screening(
                job_id=job.id,
                candidate_id=candidate.candidate_id,
                status='COMPLETED',
                evaluation={'recommendation': 'REVIEW', 'overall_score': 6},
            )
            db.add(screening)
            db.commit()
            db.refresh(screening)

            client = TestClient(app)
            response = client.post(f'/api/screenings/{screening.id}/decision', json={'decision': 'SHORTLIST'})
            self.assertEqual(response.status_code, 200, response.text)
            payload = response.json()
            self.assertEqual(payload['recruiter_decision'], 'SHORTLIST')

            list_response = client.get(f'/api/jobs/{job.id}/screenings')
            self.assertEqual(list_response.status_code, 200, list_response.text)
            rows = list_response.json()
            self.assertEqual(rows[0]['recruiter_decision'], 'SHORTLIST')
        finally:
            db.close()


if __name__ == '__main__':
    unittest.main()
