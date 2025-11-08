# server.py - FastAPI LLM proxy (mock mode)
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI()

class GenerateRequest(BaseModel):
    origin: str
    destination: str
    start_date: str
    end_date: str
    interests: List[str]
    pace: str

@app.post("/generate")
async def generate(req: GenerateRequest):
    # For development: return deterministic mock based on input
    try:
        days = []
        # Example: create one day per date (basic mock)
        days.append({
            "date": req.start_date,
            "morning": {
                "title": "Explore local market",
                "time": "09:00-11:00",
                "explain": "Great for food and local vibe."
            },
            "afternoon": {
                "title": "City museum",
                "time": "13:00-15:00",
                "explain": "Typical museum for history."
            },
            "evening": {
                "title": "Nightlife district",
                "time": "19:00-22:00",
                "explain": "Bars and street food."
            }
        })
        return {"days": days}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
