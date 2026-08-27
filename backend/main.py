from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from backend.auth.auth_utils import archive_old_logs
from backend.database.database import SessionLocal
from apscheduler.schedulers.background import BackgroundScheduler
import os
import glob
import asyncio
from backend.database.models import FileMetadata

from backend.users.router import router as users_router
from backend.data_ingestion.router import router as data_router
from backend.settings.router import router as settings_router
from backend.data_ingestion.websockets import router as websockets_router

app = FastAPI(title="UIDAI Backend API")

scheduler = BackgroundScheduler()

def process_unprocessed_files():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    uidai_data_dir = os.path.join(BASE_DIR, "uidai_data")
    if not os.path.exists(uidai_data_dir):
        return
        
    db = SessionLocal()
    try:
        indexed = {(f[0], f[1]) for f in db.query(FileMetadata.filename, FileMetadata.upload_directory).all()}
        from backend.config import get_active_folders
        active_folders = get_active_folders(db)
        
        for data_type_folder in os.listdir(uidai_data_dir):
            folder_path = os.path.join(uidai_data_dir, data_type_folder)
            if not os.path.isdir(folder_path):
                continue
            if data_type_folder.lower() not in active_folders:
                continue

            for file_path in glob.glob(os.path.join(folder_path, "**", "*.*"), recursive=True):
                filename = os.path.basename(file_path)
                if filename.startswith("~$") or filename.startswith("."):
                    continue
                upload_dir = os.path.basename(os.path.dirname(file_path))
                if (filename, upload_dir) not in indexed:
                    from backend.data_ingestion.websockets import process_file_background
                    try:
                        # Canonical mapping — .title() breaks acronyms ("Cdr Data" instead of "CDR Data")
                        FOLDER_TO_DATA_TYPE = {
                            "ccf_data": "CCF Data",
                            "cdr_data": "CDR Data",
                            "unimate_data": "UniMate Data",
                        }
                        data_type = FOLDER_TO_DATA_TYPE.get(data_type_folder.lower())
                        if data_type is None:
                            print(f"CRON: Unknown data folder '{data_type_folder}', skipping {filename}")
                            continue
                            
                        asyncio.run(process_file_background(file_path, filename, "CRON", "system_cron", data_type=data_type, meta={}))
                    except Exception as e:
                        print(f"CRON task failed for {filename}: {e}")
    except Exception as e:
        print(f"Error in CRON: {e}")
    finally:
        db.close()

@app.on_event("startup")
async def startup_event():
    # Archive logs older than 90 days on startup
    db = SessionLocal()
    try:
        archive_old_logs(db=db, days=90)
    finally:
        db.close()
        
    scheduler.add_job(process_unprocessed_files, 'interval', minutes=3)
    scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()

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
app.include_router(users_router)
app.include_router(data_router)
app.include_router(settings_router)
app.include_router(websockets_router)
