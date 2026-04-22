from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from api.config import TEMPLATES_DIR
from api.db import get_db
from api.repositories.oauth_accounts import get_primary_access_token
from api.services.dashboard import build_dashboard_context
from api.services.strava import fetch_activities

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    with get_db() as db:
        access_token = get_primary_access_token(db)

    if not access_token:
        return RedirectResponse(url="/login")

    activities = fetch_activities(access_token=access_token, per_page=20)
    context = build_dashboard_context(activities)
    context["request"] = request
    return templates.TemplateResponse(request=request, name="dashboard.html", context=context)
