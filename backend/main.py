from fastapi import FastAPI
from a2wsgi import WSGIMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from backend.audit.audit_logger import archive_old_logs
from backend.database.database import SessionLocal, engine, Base
from apscheduler.schedulers.background import BackgroundScheduler
import os
import glob
import asyncio
from backend.database.models import FileMetadata

from backend.users.router import router as users_router
from backend.data_ingestion.router import router as data_router
from backend.settings.router import router as settings_router
from backend.data_ingestion.websockets import router as websockets_router

from a2wsgi import WSGIMiddleware
from frontend.app import app as dash_app

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
                            "apr_data": "APR Data",
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

import threading

def ensure_sample_data():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(BASE_DIR, "uidai_data")
    
    folders_to_check = {
        "ccf_data": "ccf",
        "cdr_data": "cdr",
        "unimate_data": "unimate",
        "apr_data": "apr"
    }
    
    missing_modules = []
    for folder, module_name in folders_to_check.items():
        folder_path = os.path.join(data_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
        has_files = any(f for f in os.listdir(folder_path) if not f.startswith("~$") and not f.startswith("."))
        if not has_files:
            missing_modules.append(module_name)
            
    if not missing_modules:
        return
        
    print(f"Startup check: Missing data in {missing_modules}. Starting background generation...")
    
    def generate_data():
        import sys
        if BASE_DIR not in sys.path:
            sys.path.append(BASE_DIR)
            
        for mod in missing_modules:
            try:
                print(f"Generating sample data for {mod} (30 days, reduced volume)...")
                if mod == "ccf":
                    from sample_data_maker.ccf import generate_sample_ccf_data
                    generate_sample_ccf_data(daily_calls=5000, days=30)
                elif mod == "cdr":
                    from sample_data_maker.cdr import generate_sample_cdr_data
                    generate_sample_cdr_data(daily_calls=5000, days=30)
                elif mod == "unimate":
                    from sample_data_maker.unimate import generate_sample_unimate_data
                    generate_sample_unimate_data(daily_calls=5000, days=30)
                elif mod == "apr":
                    from sample_data_maker.apr import generate_sample_apr_data
                    generate_sample_apr_data(num_agents=200, days=30)
                print(f"Finished generating sample data for {mod}.")
            except Exception as e:
                print(f"Failed to generate {mod}: {e}")
                
    threading.Thread(target=generate_data, daemon=True).start()

@app.on_event("startup")
async def startup_event():
    # 1. Safely create all missing tables (handles "already exists" cleanly)
    Base.metadata.create_all(bind=engine)
    
    # 2. Tell Alembic to run migrations, or stamp if it's a new/old database
    try:
        from alembic import command
        from alembic.config import Config
        from sqlalchemy import inspect
        alembic_cfg = Config("alembic.ini")
        
        inspector = inspect(engine)
        has_alembic = inspector.has_table("alembic_version")
        has_users = inspector.has_table("users")
        
        # Determine if database needs a stamp before upgrade
        if has_users and not has_alembic:
            # Legacy database that existed before Alembic tracking
            cols = [c['name'] for c in inspector.get_columns('users')]
            if 'data_lookback_days' in cols:
                # Fully up to date manually
                command.stamp(alembic_cfg, "head")
                print("Stamped legacy database to head.")
            else:
                # Stamp to the previous migration so upgrade() applies data_lookback_days
                command.stamp(alembic_cfg, "62a625ae6135")
                print("Stamped legacy database to 62a625ae6135 (pre-lookback days).")
        elif not has_users:
            # Brand new database. create_all() already handled creation.
            command.stamp(alembic_cfg, "head")
            print("Stamped new database to head.")
            
        # Run migrations automatically
        command.upgrade(alembic_cfg, "head")
        print("Database schema is fully up to date.")
    except Exception as e:
        print(f"Warning: Failed to run alembic migrations: {e}")

    # Initialize DB session for startup tasks
    db = SessionLocal()
    try:
        # Seed default users if none exist
        from backend.database.models import User
        if db.query(User).first() is None:
            from backend.auth.auth_utils import get_password_hash
            db.add(User(username="admin", password_hash=get_password_hash("admin")))
            db.add(User(username="uidai", password_hash=get_password_hash("uidai")))
            db.flush()
            
            from backend.database.models import UserPermission
            db.add(UserPermission(user_id=1, is_admin=True, data_lookback_days=None, company_digitech=True, company_nsb=True, can_view_ccf=True, can_view_unimate=True, can_view_cdr=True, can_view_apr=True, can_download_files=True))
            db.add(UserPermission(user_id=2, is_admin=False, data_lookback_days=90, company_digitech=True, company_nsb=True, can_view_ccf=True, can_view_unimate=True, can_view_cdr=True, can_view_apr=True, can_download_files=False))
            db.commit()
            print("Startup check: Created default 'admin' and 'uidai' accounts.")
            
        # Archive logs older than 90 days on startup
        archive_old_logs(db=db, days=90)
    except Exception as e:
        print(f"Error during DB startup checks: {e}")
    finally:
        db.close()
        
    ensure_sample_data()
        
    scheduler.add_job(process_unprocessed_files, 'interval', minutes=3)
    scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()

# Add CORS Middleware to restrict to Dash frontend origin
origins = [
    "*", # Allow all since they are on the same origin now, but good to be flexible
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include Routers with /api prefix
app.include_router(users_router, prefix="/api")
app.include_router(data_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(websockets_router, prefix="/api")

# Mount Dash app
app.mount("/", WSGIMiddleware(dash_app.server))
