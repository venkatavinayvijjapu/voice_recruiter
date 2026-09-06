import json
from openai import OpenAI
from ..config import settings

client = OpenAI(base_url=settings.explabs_base_url, api_key=settings.explabs_api_key)

JD_SYSTEM = """You are an expert recruitment requirements analyst. Return ONLY valid JSON. Never invent requirements that are not supported by the job description."""

def _json(text: str):
    text = text.strip()
    try: return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start: return json.loads(text[start:end+1])
        raise

def _json_array(text: str) -> list:
    text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("["), text.rfind("]")
        if start < 0 or end <= start:
            raise
        data = json.loads(text[start:end + 1])
    return data if isinstance(data, list) else []

def chat(prompt: str) -> str:
    r = client.chat.completions.create(
        model=settings.explabs_model,
        messages=[{"role":"user","content":prompt}],
    )
    return r.choices[0].message.content or ""

def parse_jd(jd: str) -> dict:
    return _json(chat(f"""{JD_SYSTEM}
Analyze this Job Description and extract hiring requirements.
Return exactly:
{{"role":"","required_skills":[],"min_experience_years":0,"location":"","education":[]}}
Job Description:\n{jd}"""))

def generate_questions(jd: str, requirements: dict) -> list[str]:
    raw = chat(f"""You are a technical recruiter. Create exactly 5 concise screening questions for the role.
Cover experience, the most important technical skills, practical production experience, and one problem-solving question.
Return ONLY a JSON array of strings.
Requirements: {json.dumps(requirements)}
Job Description:\n{jd}""")
    data = _json_array(raw)
    return [str(x) for x in data][:5]

def evaluate_screening(jd: str, candidate: dict, call_data: dict) -> dict:
    transcript = call_data.get("transcript") or call_data.get("candidate_responses") or ""
    result = call_data.get("result") or {}
    prompt = f"""You are a careful hiring evaluator. Evaluate ONLY evidence explicitly present in the candidate profile and completed screening data. Do not infer protected characteristics or fabricate facts.
Return ONLY JSON with this schema:
{{
 "technical_score": 0,
 "communication_score": 0,
 "experience_score": 0,
 "skills_match_score": 0,
 "overall_score": 0,
 "recommendation": "SHORTLIST|REVIEW|REJECT",
 "confidence": 0.0,
 "strengths": [],
 "concerns": [],
 "summary": ""
}}
Use 0-10 scores. If evidence is insufficient, prefer REVIEW and lower confidence.
JOB:\n{jd}
CANDIDATE:\n{json.dumps(candidate)}
HUNAR RESULT:\n{json.dumps(result)}
TRANSCRIPT:\n{transcript}"""
    return _json(chat(prompt))
