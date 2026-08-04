from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from backend.api.auth_utils import archive_old_logs

from backend.api.routers import users, data, settings, websockets

app = FastAPI(title="UIDAI Backend API")

@app.on_event("startup")
async def startup_event():
    # Archive logs older than 90 days on startup
    archive_old_logs(days=90)

# Add CORS Middleware to restrict to Dash frontend origin
origins = [
    "http://localhost:8050",
    "http://127.0.0.1:8050",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include Routers
app.include_router(users.router)
app.include_router(data.router)
app.include_router(settings.router)
app.include_router(websockets.router)
