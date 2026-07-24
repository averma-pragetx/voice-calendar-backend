import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import calendar_view, calls, tools

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Voice Agent x Apple Calendar Backend",
    description="Backend connecting an ElevenLabs voice agent to a user's Apple (iCloud) Calendar via CalDAV.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(calls.router)
app.include_router(tools.router)
app.include_router(calendar_view.router)


@app.get("/health")
def health():
    return {"status": "ok"}
