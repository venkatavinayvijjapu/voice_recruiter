from app.db import Base,engine,SessionLocal
from app.models import Candidate, User
from app.api.auth import get_password_hash

Base.metadata.create_all(bind=engine)
db=SessionLocal()

if not db.query(User).first():
    db.add_all([
        User(email='admin1@example.com', hashed_password=get_password_hash('password123')),
        User(email='admin2@example.com', hashed_password=get_password_hash('password456')),
        User(email='admin3@example.com', hashed_password=get_password_hash('password789'))
    ])
    db.commit()

if not db.query(Candidate).first():
 db.add_all([
  Candidate(name='Rahul Kumar',email='rahul@example.com',phone='+918341646167',location='Bangalore',experience_years=7,current_company='ABC Technologies',current_title='Senior Python Developer',skills='Python, FastAPI, AWS, PostgreSQL, Docker, Kubernetes'),
  Candidate(name='Amit Singh',email='amit@example.com',phone='+917013781536',location='Bangalore',experience_years=4,current_company='Tech Corp',current_title='Software Engineer',skills='Python, FastAPI, AWS, PostgreSQL')])
 db.commit()
print('seed complete')

