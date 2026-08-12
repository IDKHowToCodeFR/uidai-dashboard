import os
import io
import pandas as pd
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from backend.auth.auth_utils import get_current_user, PermissionChecker, add_log
from backend.database.database import get_db
from backend.database.models import FileMetadata, CallMetric
from backend.data_ingestion.websockets import process_file_background

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UNPROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "unprocessed")

router = APIRouter()

@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    client_id: str = Form(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_role = current_user["role"]
    permissions = current_user.get("permissions", [])
    
    if "can_upload_files" not in permissions:
        raise HTTPException(status_code=403, detail="You do not have permission to upload files.")
        
    prefix = f"{user_role}_" if user_role and user_role != 'Admin' else "Admin_"
    safe_filename = os.path.basename(file.filename)
    out_filename = prefix + safe_filename
    
    os.makedirs(UNPROCESSED_DATA_DIR, exist_ok=True)
    save_path = os.path.abspath(os.path.join(UNPROCESSED_DATA_DIR, out_filename))
    
    if not save_path.startswith(os.path.abspath(UNPROCESSED_DATA_DIR)):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    contents = await file.read()
    
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
        
    # Standard practice: Store raw file in codebase first
    with open(save_path, "wb") as f:
        f.write(contents)
        
    if client_id:
        background_tasks.add_task(process_file_background, save_path, out_filename, client_id, current_user["username"])
        return {"message": "Processing started", "status": "processing"}
    else:
        # We don't support synchronous upload without client_id anymore because it's an ETL pipeline
        raise HTTPException(status_code=400, detail="client_id is required for ETL processing")


@router.get("/history")
async def get_history(impersonate: Optional[str] = None, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    files = db.query(FileMetadata).order_by(FileMetadata.uploaded_at.desc()).all()
    
    file_times = []
    for f in files:
        file_times.append({
            'name': f.filename, 
            'time': f.uploaded_at,
            'size': f.size_bytes,
            'uploader': f.uploader
        })
    
    return file_times


@router.get("/data/aggregate")
async def get_aggregated_data(impersonate: Optional[str] = None, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(CallMetric)
    
    if impersonate:
        query = query.filter(CallMetric.company == impersonate)
            
    metrics = query.all()
    # Serialize
    return [
        {
            "Company": m.company,
            "Language": m.language,
            "Date": m.date_logged,
            "Call Timestamp": m.call_timestamp,
            "Day": m.day,
            "Call Offered": m.call_offered,
            "ABAN Calls in 10 Sec": m.aban_calls_10_sec,
            "ACD Calls in 10 Sec": m.acd_calls_10_sec,
            "ACD Calls in 20 Sec": m.acd_calls_20_sec,
            "ABAN Calls": m.aban_calls,
            "Held Calls": m.held_calls,
            "Service Level %": m.service_level_pct,
            "Service Level Status": m.service_level_status,
            "ACD Calls": m.acd_calls,
            "Hold Time": m.hold_time,
            "Avg Hold Time": m.avg_hold_time,
            "Hold Time Status": m.hold_time_status,
            "ACD Time": m.acd_time,
            "ACW Time": m.acw_time,
            "Avg Handle Time": m.avg_handle_time,
            "AHT Status": m.aht_status
        } for m in metrics
    ]


@router.get("/data/{filename}")
async def get_data(filename: str, impersonate: Optional[str] = None, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    file_meta = db.query(FileMetadata).filter(FileMetadata.filename == filename).first()
    if not file_meta:
        raise HTTPException(status_code=404, detail="File not found")
        
    query = db.query(CallMetric).filter(CallMetric.file_id == file_meta.id)
    
    if impersonate:
        query = query.filter(CallMetric.company == impersonate)
        
    metrics = query.all()
    return [
        {
            "Company": m.company,
            "Language": m.language,
            "Date": m.date_logged,
            "Call Timestamp": m.call_timestamp,
            "Day": m.day,
            "Call Offered": m.call_offered,
            "ABAN Calls in 10 Sec": m.aban_calls_10_sec,
            "ACD Calls in 10 Sec": m.acd_calls_10_sec,
            "ACD Calls in 20 Sec": m.acd_calls_20_sec,
            "ABAN Calls": m.aban_calls,
            "Held Calls": m.held_calls,
            "Service Level %": m.service_level_pct,
            "Service Level Status": m.service_level_status,
            "ACD Calls": m.acd_calls,
            "Hold Time": m.hold_time,
            "Avg Hold Time": m.avg_hold_time,
            "Hold Time Status": m.hold_time_status,
            "ACD Time": m.acd_time,
            "ACW Time": m.acw_time,
            "Avg Handle Time": m.avg_handle_time,
            "AHT Status": m.aht_status
        } for m in metrics
    ]


@router.get("/download/{filename}")
async def download_file(filename: str, impersonate: Optional[str] = None, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    file_meta = db.query(FileMetadata).filter(FileMetadata.filename == filename).first()
    if not file_meta:
        raise HTTPException(status_code=404, detail="File not found")
        
    # Serve the original raw file from unprocessed
    safe_filename = os.path.basename(filename)
    file_path = os.path.abspath(os.path.join(UNPROCESSED_DATA_DIR, safe_filename))
    
    if os.path.exists(file_path):
        add_log(db, "FILE_DOWNLOADED", current_user["username"], f"Downloaded raw file: {safe_filename}")
        return FileResponse(file_path, filename=safe_filename)
    else:
        raise HTTPException(status_code=404, detail="Raw file not found on disk")
