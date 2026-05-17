from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from api.config import TEMPLATES_DIR
from api.db import get_db
from api.services.auth_tokens import get_valid_access_token
from api.services.dashboard import build_dashboard_context
from api.services.strava import fetch_activities

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)

ATHLETE_COOKIE_NAME = "athlete_id"


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    # Get athlete_id from session cookie to identify current user
    athlete_id = request.cookies.get(ATHLETE_COOKIE_NAME)
    if not athlete_id:
        return RedirectResponse(url="/login")

    with get_db() as db:
        access_token = get_valid_access_token(db, athlete_id=athlete_id)

    if not access_token:
        return RedirectResponse(url="/login")

    activities = fetch_activities(access_token=access_token, per_page=20)
    context = build_dashboard_context(activities)
    context["request"] = request
    return templates.TemplateResponse(request=request, name="dashboard.html", context=context)
