from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.health import router as health_router
from app.routers.ingest import router as ingest_router
from app.routers.opportunities import router as opportunities_router


app = FastAPI(title="trackers-dashboard-api")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{settings.web_port}", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(opportunities_router)
