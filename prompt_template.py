# prompt_template.py
import json
from datetime import datetime, timedelta

def build_prompt(payload: dict) -> str:
    # Tính số ngày
    start = datetime.fromisoformat(payload["start_date"])
    end = datetime.fromisoformat(payload["end_date"])
    num_days = (end - start).days + 1

    # Chuẩn bị danh sách ngày
    dates = [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(num_days)]

    template = f"""
You are an intelligent travel planning AI.
Generate a detailed {num_days}-day itinerary.

Origin: {payload['origin']}
Destination: {payload['destination']}
Dates: {payload['start_date']} → {payload['end_date']}
Interests: {", ".join(payload['interests'])}
Travel pace: {payload['pace']}

✅ Output format requirement:
Return ONLY a valid JSON object:
{{
  "days": [
    {{
      "date": "YYYY-MM-DD",
      "morning": {{
        "time": "short string",
        "title": "short string",
        "explain": "one sentence"
      }},
      "afternoon": {{
        "time": "short string",
        "title": "short string",
        "explain": "one sentence"
      }},
      "evening": {{
        "time": "short string",
        "title": "short string",
        "explain": "one sentence"
      }}
    }}
  ]
}}


{json.dumps(dates)}
"""

    return template.strip()


def parse_model_output(text: str):
    # LLM sometimes wraps JSON inside text -> extract block
    try:
        first = text.find("{")
        last = text.rfind("}")
        clean = text[first:last+1]
        return json.loads(clean)
    except Exception:
        return None
