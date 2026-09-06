from app.db import Base,engine,SessionLocal
from app.models import Candidate
Base.metadata.create_all(bind=engine)
db=SessionLocal()
if not db.query(Candidate).first():
 db.add_all([
  Candidate(name='Rahul Kumar',email='rahul@example.com',phone='+910000000001',location='Bangalore',experience_years=7,current_company='ABC Technologies',current_title='Senior Python Developer',skills='Python, FastAPI, AWS, PostgreSQL, Docker, Kubernetes'),
  Candidate(name='Amit Singh',email='amit@example.com',phone='+910000000002',location='Bangalore',experience_years=4,current_company='Tech Corp',current_title='Software Engineer',skills='Python, FastAPI, AWS, PostgreSQL')])
 db.commit()
print('seed complete')
