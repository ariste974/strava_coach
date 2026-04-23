from pydantic import BaseModel, Field
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from api.config import TEMPLATES_DIR, require_env
from api.db import get_db
from api.services.auth_tokens import get_valid_access_token
from api.services.coach import build_coach_system_prompt, build_training_snapshot
from api.services.gemini import generate_coaching_response
from api.services.strava import fetch_activities

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class CoachChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)


def _load_training_snapshot() -> dict:
    with get_db() as db:
        access_token = get_valid_access_token(db)

    if not access_token:
        return {}

    activities = fetch_activities(access_token=access_token, per_page=40)
    return build_training_snapshot(activities)


@router.get("/coach", response_class=HTMLResponse)
def coach_page(request: Request):
    require_env("GEMINI_API_KEY")

    snapshot = _load_training_snapshot()
    if not snapshot:
        return RedirectResponse(url="/login")

    context = {
        "request": request,
        "summary": snapshot["athlete_context"],
    }
    return templates.TemplateResponse(request=request, name="coach.html", context=context)


@router.post("/api/coach/chat")
def coach_chat(payload: CoachChatRequest):
    require_env("GEMINI_API_KEY")

    snapshot = _load_training_snapshot()
    if not snapshot:
        return JSONResponse(status_code=401, content={"detail": "Utilisateur non connecte"})

    message_history = [message.model_dump() for message in payload.history]
    message_history.append({"role": "user", "content": payload.message})
    print(build_coach_system_prompt(snapshot["summary_text"]))
    answer = generate_coaching_response(
        system_prompt=build_coach_system_prompt(snapshot["summary_text"]),
        history=message_history,
    )
    print("Gemini answer:", answer)
    return {"reply": answer}
