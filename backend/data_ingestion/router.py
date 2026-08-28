import os
import io
import pandas as pd
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from backend.auth.auth_utils import get_current_user, require_permission
from backend.audit.audit_logger import add_log, extract_request_metadata
from backend.database.database import get_db
from backend.database.models import FileMetadata, CCFData, UniMateData, CDRData
from backend.data_ingestion.websockets import process_file_background

def serialize_data(metrics, data_type):
    if data_type == "UniMate Data":
        return [
            {
                "UCID": m.ucid,
                "Session ID": m.session_id,
                "Company": m.company,
                "Day of Week": m.day_of_week,
                "Call Start Time": m.call_start_time,
                "Call End Time": m.call_end_time,
                "Call Duration": m.call_duration,
                "ANI": m.ani,
                "DNIS": m.dnis,
                "Language": m.language,
                "Authentication": m.authentication,
                "Authentication Mechanism": m.auth_mechanism,
                "Termination Type": m.termination_type,
                "Termination Reason": m.termination_reason,
                "Description": m.description,
                "Region": m.region
            } for m in metrics
        ]
    elif data_type == "CDR Data":
        return [
            {
                "Call Id": m.call_id,
                "acwtime": m.acwtime,
                "ansholdtime": m.ansholdtime,
                "duration": m.duration,
                "segstart": m.segstart,
                "segstartutc": m.segstartutc,
                "segstop": m.segstop,
                "segstoputc": m.segstoputc,
                "talktime": m.talktime,
                "split1": m.split1,
                "transferred": m.transferred,
                "agt_released": m.agt_released,
                "origlogin": m.origlogin,
                "anslogin": m.anslogin,
                "Company": m.company,
                "Language": m.language
            } for m in metrics
        ]
    else:
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
                "ACD Calls": m.acd_calls,
                "Hold Time": m.hold_time,
                "ACD Time": m.acd_time,
                "ACW Time": m.acw_time
            } for m in metrics
        ]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UIDAI_DATA_DIR = os.path.join(BASE_DIR, "uidai_data")

router = APIRouter()


FOLDER_TO_DATA_TYPE = {
    "ccf_data": "CCF Data",
    "cdr_data": "CDR Data",
    "unimate_data": "UniMate Data",
    "apr_data": "APR Data",
}

@router.get("/companies")
def get_all_companies(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.database.models import CCFData, UniMateData, CDRData, APRData
    c1 = [r[0] for r in db.query(CCFData.company).distinct().all() if r[0]]
    c2 = [r[0] for r in db.query(UniMateData.company).distinct().all() if r[0]]
    c3 = [r[0] for r in db.query(CDRData.company).distinct().all() if r[0]]
    c4 = [r[0] for r in db.query(APRData.company).distinct().all() if r[0]]
    companies = sorted(list(set(c1 + c2 + c3 + c4)))
    if not companies:
        companies = ["Digitech", "NSB"]
        
    user_companies = current_user.get("companies", [])
    if current_user.get("username", "").lower() != "admin" and user_companies:
        companies = [c for c in companies if c in user_companies]
        
    return companies


@router.get("/data_types")
async def get_data_types(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if not os.path.exists(UIDAI_DATA_DIR):
        return ["CCF Data"]
        
    folders = [d for d in os.listdir(UIDAI_DATA_DIR) if os.path.isdir(os.path.join(UIDAI_DATA_DIR, d))]
    valid_types = [FOLDER_TO_DATA_TYPE[f] for f in folders if f in FOLDER_TO_DATA_TYPE]
    if not valid_types:
        valid_types = ["CCF Data"]
    return valid_types


@router.get("/history")
async def get_history(data_type: Optional[str] = None, impersonate: Optional[str] = None, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user_companies = current_user.get("companies", [])
    permissions = current_user.get("permissions", [])
    is_global = current_user.get("role") == "Admin" or "can_view_global" in permissions
    
    query = db.query(FileMetadata)
    if data_type:
        query = query.filter(FileMetadata.data_type == data_type)
    
    target_company = None
    if is_global:
        if impersonate:
            target_company = impersonate
    else:
        if impersonate:
            if impersonate not in user_companies:
                raise HTTPException(status_code=403, detail="Access denied.")
            target_company = impersonate
        else:
            # Filter files containing data for the user's scoped companies
            if data_type == "UniMate Data":
                query = query.filter(FileMetadata.unimate_metrics.any(UniMateData.company.in_(user_companies)))
            elif data_type == "CDR Data":
                query = query.filter(FileMetadata.cdr_metrics.any(CDRData.company.in_(user_companies)))
            elif data_type == "APR Data":
                from backend.database.models import APRData
                query = query.filter(FileMetadata.apr_metrics.any(APRData.company.in_(user_companies)))
            else:
                query = query.filter(FileMetadata.metrics.any(CCFData.company.in_(user_companies)))
                
    if target_company:
        if data_type == "UniMate Data":
            query = query.filter(FileMetadata.unimate_metrics.any(UniMateData.company == target_company))
        elif data_type == "CDR Data":
            query = query.filter(FileMetadata.cdr_metrics.any(CDRData.company == target_company))
        elif data_type == "APR Data":
            from backend.database.models import APRData
            query = query.filter(FileMetadata.apr_metrics.any(APRData.company == target_company))
        else:
            query = query.filter(FileMetadata.metrics.any(CCFData.company == target_company))
            
    files = query.order_by(FileMetadata.uploaded_at.desc()).all()
    
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
async def get_aggregated_data(data_type: str = "CCF Data", impersonate: Optional[str] = None, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if data_type == "UniMate Data":
        model_class = UniMateData
    elif data_type == "CDR Data":
        model_class = CDRData
    elif data_type == "APR Data":
        from backend.database.models import APRData
        model_class = APRData
    else:
        model_class = CCFData
        
    query = db.query(model_class)
    
    user_companies = current_user.get("companies", [])
    permissions = current_user.get("permissions", [])
    is_global = current_user.get("role") == "Admin" or "can_view_global" in permissions
    
    if is_global:
        if impersonate:
            query = query.filter(model_class.company == impersonate)
    else:
        if impersonate:
            if impersonate not in user_companies:
                raise HTTPException(status_code=403, detail="Access denied to this company.")
            query = query.filter(model_class.company == impersonate)
        else:
            query = query.filter(model_class.company.in_(user_companies))
            
    metrics = query.all()
    return serialize_data(metrics, data_type)
    
    
@router.get("/data/{filename}")
async def get_data(filename: str, impersonate: Optional[str] = None, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    file_meta = db.query(FileMetadata).filter(FileMetadata.filename == filename).first()
    if not file_meta:
        raise HTTPException(status_code=404, detail="File not found")
        
    if file_meta.data_type == "UniMate Data":
        model_class = UniMateData
    elif file_meta.data_type == "CDR Data":
        model_class = CDRData
    else:
        model_class = CCFData
        
    query = db.query(model_class).filter(model_class.file_id == file_meta.id)
    
    user_companies = current_user.get("companies", [])
    permissions = current_user.get("permissions", [])
    is_global = current_user.get("role") == "Admin" or "can_view_global" in permissions
    
    if is_global:
        if impersonate:
            query = query.filter(model_class.company == impersonate)
    else:
        if impersonate:
            if impersonate not in user_companies:
                raise HTTPException(status_code=403, detail="Access denied to this company.")
            query = query.filter(model_class.company == impersonate)
        else:
            query = query.filter(model_class.company.in_(user_companies))
            
    metrics = query.all()
    return serialize_data(metrics, file_meta.data_type)
    
    
@router.get("/download/{filename}")
async def download_file(request: Request, filename: str, impersonate: Optional[str] = None, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    file_meta = db.query(FileMetadata).filter(FileMetadata.filename == filename).order_by(FileMetadata.id.desc()).first()
    if not file_meta:
        raise HTTPException(status_code=404, detail="File not found")
        
    user_companies = current_user.get("companies", [])
    permissions = current_user.get("permissions", [])
    is_global = current_user.get("role") == "Admin" or "can_view_global" in permissions
    
    # Restrict raw file downloads to global viewers only
    if not impersonate and is_global:
        safe_data_type = "".join([c if c.isalnum() else "_" for c in file_meta.data_type.lower()])
        file_path = os.path.join(UIDAI_DATA_DIR, safe_data_type, filename)
        
        if os.path.exists(file_path):
            meta = extract_request_metadata(request)
            add_log(db, "FILE_DOWNLOADED", current_user["username"], f"Downloaded raw file: {filename}", **meta)
            headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
            return FileResponse(file_path, headers=headers, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
    if file_meta.data_type == "UniMate Data":
        model_class = UniMateData
    elif file_meta.data_type == "CDR Data":
        model_class = CDRData
    else:
        model_class = CCFData
        
    query = db.query(model_class).filter(model_class.file_id == file_meta.id)
    
    if is_global:
        if impersonate:
            query = query.filter(model_class.company == impersonate)
    else:
        if impersonate:
            if impersonate not in user_companies:
                raise HTTPException(status_code=403, detail="Access denied to this company.")
            query = query.filter(model_class.company == impersonate)
        else:
            query = query.filter(model_class.company.in_(user_companies))
            
    metrics = query.all()
    if not metrics:
        raise HTTPException(status_code=404, detail="No data available for this file")
        
    data = serialize_data(metrics, file_meta.data_type)
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Report')
    
    output.seek(0)
    
    safe_filename = os.path.basename(filename)
    base_name = os.path.splitext(safe_filename)[0]
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    if file_meta.data_type == "UniMate Data":
        export_prefix = "UniMate_Report"
    elif file_meta.data_type == "CDR Data":
        export_prefix = "CDR_Report"
    else:
        export_prefix = "CCF_Report"
        
    export_filename = f"{export_prefix}_{base_name}_{today_str}.xlsx"
    
    meta = extract_request_metadata(request)
    add_log(db, "FILE_DOWNLOADED", current_user["username"], f"Downloaded report: {export_filename}", **meta)
    
    headers = {
        'Content-Disposition': f'attachment; filename="{export_filename}"'
    }
    
    return StreamingResponse(output, headers=headers, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
# --- Dedicated Dashboard APIs ---

@router.get("/dashboards/ccf/metrics")
async def get_ccf_metrics(impersonate: Optional[str] = None, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return await get_aggregated_data(data_type="CCF Data", impersonate=impersonate, current_user=current_user, db=db)

@router.get("/dashboards/unimate/metrics")
async def get_unimate_metrics(impersonate: Optional[str] = None, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return await get_aggregated_data(data_type="UniMate Data", impersonate=impersonate, current_user=current_user, db=db)

@router.get("/dashboards/cdr/metrics")
async def get_cdr_metrics(impersonate: Optional[str] = None, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return await get_aggregated_data(data_type="CDR Data", impersonate=impersonate, current_user=current_user, db=db)
