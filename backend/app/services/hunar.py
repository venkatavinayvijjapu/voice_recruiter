import httpx
from ..config import settings

class HunarClient:
    def __init__(self):
        self.base = settings.hunar_base_url.rstrip("/")
        self.headers = {"X-API-Key": settings.hunar_api_key, "Content-Type": "application/json"}

    def create_bulk(self, rows: list[dict], request_id: str):
        payload = {
            "agent_id": settings.hunar_agent_id,
            "request_id": request_id,
            "data": rows,
            "timezone": "Asia/Kolkata",
            "remove_invalid_rows": True,
            "remove_duplicate_phone_numbers": True,
        }
        with httpx.Client(timeout=60) as c:
            r = c.post(f"{self.base}/calls/bulk/", headers=self.headers, json=payload)
            if r.is_error:
                raise RuntimeError(f"Hunar rejected bulk call ({r.status_code}): {r.text}")
            return r.json()

    def get_call(self, call_id: str):
        with httpx.Client(timeout=30) as c:
            r = c.get(f"{self.base}/calls/{call_id}/", headers=self.headers)
            r.raise_for_status()
            return r.json()
