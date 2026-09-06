# AI Hiring Assistant

Production-oriented recruitment screening application based on the provided `hiring.ipynb` flow.

## Stack
- FastAPI
- PostgreSQL
- Redis + Celery worker
- Next.js frontend
- GPT-6 Astra through the Experiential Labs OpenAI-compatible API
- Hunar AI Voice API

Ollama is intentionally not included.

## Flow
1. Recruiter creates a job and submits a JD.
2. GPT-6 Astra extracts structured requirements and generates screening questions.
3. Backend matches candidates in PostgreSQL.
4. Recruiter selects candidates and starts AI screening.
5. Hunar bulk calls are created.
6. Celery polls Hunar until calls reach a terminal state.
7. Completed call data is stored, including transcript/result/recording URL when supplied.
8. GPT-6 Astra evaluates the completed screening and produces scores plus SHORTLIST/REVIEW/REJECT.
9. Dashboard displays live statuses and candidate evaluations.

## Security
Rotate/revoke any Hunar key previously exposed in the notebook. Put replacement credentials only in `.env` or your deployment secret manager.

## Run
```bash
cp .env.example .env
# edit .env

docker compose up --build
```

Frontend: http://localhost:3000
API docs: http://localhost:8000/docs

## Development without Docker
Backend:
```bash
cd backend
python -m venv .venv
# activate it
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Worker:
```bash
cd backend
celery -A app.worker.celery_app worker --loglevel=INFO
```

## Notes
The exact Hunar API behavior should be validated against your active Hunar account before production launch. The implementation follows the endpoints and payload shapes demonstrated by the supplied notebook.
