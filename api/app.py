from fastapi import FastAPI

from api.routers.auth import router as auth_router
from api.routers.coach import router as coach_router
from api.routers.dashboard import router as dashboard_router


def create_app() -> FastAPI:
    app = FastAPI(title="Strava Dashboard")
    app.include_router(auth_router)
    app.include_router(dashboard_router)
    app.include_router(coach_router)
    return app
