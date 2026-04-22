import requests
from fastapi import HTTPException

from api.config import GEMINI_API_KEY, GEMINI_MODEL


GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def generate_coaching_response(system_prompt: str, history: list[dict]) -> str:
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Missing environment variables: GEMINI_API_KEY")

    contents = []
    for message in history:
        role = "model" if message.get("role") == "assistant" else "user"
        contents.append(
            {
                "role": role,
                "parts": [{"text": message.get("content", "")}],
            }
        )

    payload = {
        "systemInstruction": {
            "parts": [{"text": system_prompt}],
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.95,
            "maxOutputTokens": 1024,
        },
    }

    try:
        response = requests.post(
            GEMINI_API_URL.format(model=GEMINI_MODEL),
            params={"key": GEMINI_API_KEY},
            json=payload,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Gemini request failed: {exc}") from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail={"gemini_status": response.status_code, "body": response.text},
        )

    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise HTTPException(status_code=502, detail="Gemini returned no candidates")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts if part.get("text"))
    if not text.strip():
        raise HTTPException(status_code=502, detail="Gemini returned an empty response")
    return text.strip()
