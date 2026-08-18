import os
import io
import pandas as pd
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from backend.auth.auth_utils import get_current_user, PermissionChecker, add_log, extract_request_metadata
from backend.database.database import get_db
from backend.database.models import FileMetadata, CCFData
from backend.data_ingestion.websockets import process_file_background

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UIDAI_DATA_DIR = os.path.join(BASE_DIR, "uidai_data")

router = APIRouter()

@router.post("/upload")
async def upload_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    client_id: str = Form(None),
    data_type: str = Form("CCF Data"),
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
    
    safe_data_type = "".join([c if c.isalnum() else "_" for c in data_type.lower()])
    unprocessed_dir = os.path.join(UIDAI_DATA_DIR, safe_data_type)
    os.makedirs(unprocessed_dir, exist_ok=True)
    
    save_path = os.path.abspath(os.path.join(unprocessed_dir, out_filename))
    
    if not save_path.startswith(os.path.abspath(unprocessed_dir)):
        raise HTTPException(status_code=400, detail="Invalid filename")
        
    if file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV files are not allowed. Please upload an Excel file (.xlsx, .xls)")
    
    contents = await file.read()
    
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
        
    # Standard practice: Store raw file in codebase first
    with open(save_path, "wb") as f:
        f.write(contents)
        
    if client_id:
        meta = extract_request_metadata(request)
        background_tasks.add_task(process_file_background, save_path, out_filename, client_id, current_user["username"], data_type, meta)
        return {"message": "Processing started", "status": "processing"}
    else:
        # We don't support synchronous upload without client_id anymore because it's an ETL pipeline
        raise HTTPException(status_code=400, detail="client_id is required for ETL processing")


@router.get("/data_types")
async def get_data_types(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not os.path.exists(UIDAI_DATA_DIR):
        return ["CCF Data"]
        
    folders = [d for d in os.listdir(UIDAI_DATA_DIR) if os.path.isdir(os.path.join(UIDAI_DATA_DIR, d))]
    valid_types = [f.replace("_", " ").title() for f in folders]
    if not valid_types:
        valid_types = ["CCF Data"]
    return valid_types


@router.get("/history")
async def get_history(impersonate: Optional[str] = None, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    files = db.query(FileMetadata).order_by(FileMetadata.uploaded_at.desc()).all()
    
    file_times = []
    for f in files:
        file_times.append({
            'name': f.filename, 
            'time': f.uploaded_at,
            'size': f.size_bytes,
            'uploader': f.uploader,
            'data_type': getattr(f, 'data_type', 'CCF Data')
        })
    
    return file_times


@router.get("/data/aggregate")
async def get_aggregated_data(impersonate: Optional[str] = None, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(CCFData)
    
    if impersonate:
        query = query.filter(CCFData.company == impersonate)
            
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
        
    query = db.query(CCFData).filter(CCFData.file_id == file_meta.id)
    
    if impersonate:
        query = query.filter(CCFData.company == impersonate)
        
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
async def download_file(request: Request, filename: str, impersonate: Optional[str] = None, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    file_meta = db.query(FileMetadata).filter(FileMetadata.filename == filename).order_by(FileMetadata.id.desc()).first()
    if not file_meta:
        raise HTTPException(status_code=404, detail="File not found")
        
    if not impersonate:
        safe_data_type = "".join([c if c.isalnum() else "_" for c in file_meta.data_type.lower()])
        file_path = os.path.join(UIDAI_DATA_DIR, safe_data_type, filename)
        
        if os.path.exists(file_path):
            meta = extract_request_metadata(request)
            add_log(db, "FILE_DOWNLOADED", current_user["username"], f"Downloaded raw file: {filename}", **meta)
            headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
            return FileResponse(file_path, headers=headers, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
    query = db.query(CCFData).filter(CCFData.file_id == file_meta.id)
    
    if impersonate:
        query = query.filter(CCFData.company == impersonate)
        
    metrics = query.all()
    if not metrics:
        raise HTTPException(status_code=404, detail="No data available for this file")
        
    data = [{
        "Company": m.company, "Language": m.language, "Date": m.date_logged,
        "Call Timestamp": m.call_timestamp, "Day": m.day, "Call Offered": m.call_offered,
        "ABAN Calls in 10 Sec": m.aban_calls_10_sec, "ACD Calls in 10 Sec": m.acd_calls_10_sec,
        "ACD Calls in 20 Sec": m.acd_calls_20_sec, "ABAN Calls": m.aban_calls,
        "Held Calls": m.held_calls, "Service Level %": m.service_level_pct,
        "Service Level Status": m.service_level_status, "ACD Calls": m.acd_calls,
        "Hold Time": m.hold_time, "Avg Hold Time": m.avg_hold_time,
        "Hold Time Status": m.hold_time_status, "ACD Time": m.acd_time,
        "ACW Time": m.acw_time, "Avg Handle Time": m.avg_handle_time,
        "AHT Status": m.aht_status
    } for m in metrics]

    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Report')
    
    output.seek(0)
    
    safe_filename = os.path.basename(filename)
    base_name = os.path.splitext(safe_filename)[0]
    today_str = datetime.now().strftime("%Y-%m-%d")
    export_filename = f"CCF_Report_{base_name}_{today_str}.xlsx"
    
    meta = extract_request_metadata(request)
    add_log(db, "FILE_DOWNLOADED", current_user["username"], f"Downloaded report: {export_filename}", **meta)
    
    headers = {
        'Content-Disposition': f'attachment; filename="{export_filename}"'
    }
    
    return StreamingResponse(output, headers=headers, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
