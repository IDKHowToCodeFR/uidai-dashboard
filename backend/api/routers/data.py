import os
import io
import pandas as pd
from datetime import datetime
from typing import Optional
from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse

from backend.api.auth_utils import (
    get_current_user, PermissionChecker, add_log, BASE_DIR
)
from backend.api.routers.websockets import process_file_background

router = APIRouter()

PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")

@lru_cache(maxsize=32)
def load_data_cached(file_path: str, mtime: float):
    df = pd.read_csv(file_path)
    return df.to_dict('records')

@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    client_id: str = Form(None),
    current_user: dict = Depends(get_current_user)
):
    user_role = current_user["role"]
    permissions = current_user.get("permissions", [])
    
    if "can_upload_files" not in permissions:
        raise HTTPException(status_code=403, detail="You do not have permission to upload files.")
        
    prefix = f"{user_role}_" if user_role and user_role != 'Admin' else "Admin_"
    safe_filename = os.path.basename(file.filename)
    out_filename = prefix + os.path.splitext(safe_filename)[0] + "_processed.csv"
    save_path = os.path.abspath(os.path.join(PROCESSED_DATA_DIR, out_filename))
    
    if not save_path.startswith(os.path.abspath(PROCESSED_DATA_DIR)):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    
    contents = await file.read()
    
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
        
    if client_id:
        background_tasks.add_task(process_file_background, contents, safe_filename, save_path, client_id, current_user["username"], out_filename)
        return {"message": "Processing started", "status": "processing"}
    else:
        try:
            if safe_filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(contents))
                df.columns = df.columns.str.strip()
            elif safe_filename.endswith('.xls') or safe_filename.endswith('.xlsx'):
                excel_file = pd.ExcelFile(io.BytesIO(contents), engine='openpyxl')
                dfs = []
                for sheet_name in excel_file.sheet_names:
                    sheet_df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    sheet_df.columns = sheet_df.columns.str.strip()
                    if 'Company' not in sheet_df.columns:
                        sheet_df['Company'] = sheet_name
                    dfs.append(sheet_df)
                df = pd.concat(dfs, ignore_index=True)
            else:
                raise HTTPException(status_code=400, detail="Invalid file type. Must be csv or excel.")
                
            df.dropna(how='all', inplace=True)
            df.dropna(axis=1, how='all', inplace=True)

            numeric_cols = df.select_dtypes(include='number').columns
            df[numeric_cols] = df[numeric_cols].fillna(0)
            object_cols = df.select_dtypes(include=['object', 'string']).columns
            df[object_cols] = df[object_cols].fillna('Unknown')
            for col in object_cols:
                df[col] = df[col].astype(str).str.strip()
            
            df.to_csv(save_path, index=False)
            add_log("FILE_UPLOADED", current_user["username"], f"Uploaded file: {out_filename}")
            return {"message": "Upload complete", "status": "complete"}
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_history(impersonate: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    user_role = current_user["role"]
    permissions = current_user.get("permissions", [])
    
    if not os.path.exists(PROCESSED_DATA_DIR):
        return []
    
    files = [f for f in os.listdir(PROCESSED_DATA_DIR) if f.endswith('.csv')]
    
    if 'can_view_global' in permissions and impersonate:
        prefix = f"{impersonate}_"
        files = [f for f in files if f.startswith(prefix)]
    elif 'can_view_global' not in permissions:
        if 'can_view_scoped' in permissions:
            prefix = f"{user_role}_"
            files = [f for f in files if f.startswith(prefix)]
        else:
            files = []

    file_times = []
    for f in files:
        file_path = os.path.join(PROCESSED_DATA_DIR, f)
        stat = os.stat(file_path)
        mtime = datetime.fromtimestamp(stat.st_mtime)
        size = stat.st_size
        uploader = f.split('_')[0] if '_' in f else 'Unknown'
        file_times.append({
            'name': f, 
            'time': mtime.isoformat(),
            'size': size,
            'uploader': uploader
        })
    
    file_times.sort(key=lambda x: x['time'], reverse=True)
    return file_times


@router.get("/data/aggregate")
async def get_aggregated_data(impersonate: Optional[str] = None, current_user: dict = Depends(PermissionChecker("can_view_global"))):
    all_data = []
    if not os.path.exists(PROCESSED_DATA_DIR):
        return all_data
        
    for filename in os.listdir(PROCESSED_DATA_DIR):
        if filename.endswith(".csv"):
            if impersonate and not filename.startswith(f"{impersonate}_"):
                continue
            file_path = os.path.join(PROCESSED_DATA_DIR, filename)
            mtime = os.path.getmtime(file_path)
            data = load_data_cached(file_path, mtime)
            all_data.extend(data)
            
    return all_data


@router.get("/data/{filename}")
async def get_data(filename: str, impersonate: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    user_role = current_user["role"]
    permissions = current_user.get("permissions", [])
    
    safe_filename = os.path.basename(filename)
    file_path = os.path.abspath(os.path.join(PROCESSED_DATA_DIR, safe_filename))
    
    if not file_path.startswith(os.path.abspath(PROCESSED_DATA_DIR)):
        raise HTTPException(status_code=400, detail="Invalid filename")
        
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    if 'can_view_global' in permissions and impersonate:
        if not safe_filename.startswith(f"{impersonate}_"):
            raise HTTPException(status_code=403, detail="Access denied while impersonating")
    elif 'can_view_global' not in permissions:
        if 'can_view_scoped' not in permissions or not safe_filename.startswith(f"{user_role}_"):
            raise HTTPException(status_code=403, detail="Access denied to this file")
        
    mtime = os.path.getmtime(file_path)
    data = load_data_cached(file_path, mtime)
    return data


@router.get("/download/{filename}")
async def download_file(filename: str, impersonate: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    user_role = current_user["role"]
    permissions = current_user.get("permissions", [])
    
    safe_filename = os.path.basename(filename)
    file_path = os.path.abspath(os.path.join(PROCESSED_DATA_DIR, safe_filename))
    
    if not file_path.startswith(os.path.abspath(PROCESSED_DATA_DIR)):
        raise HTTPException(status_code=400, detail="Invalid filename")
        
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    if 'can_download_files' not in permissions:
        raise HTTPException(status_code=403, detail="Download permission denied")
        
    if 'can_view_global' in permissions and impersonate:
        if not safe_filename.startswith(f"{impersonate}_"):
            raise HTTPException(status_code=403, detail="Access denied while impersonating")
    elif 'can_view_global' not in permissions:
        if 'can_view_scoped' not in permissions or not safe_filename.startswith(f"{user_role}_"):
            raise HTTPException(status_code=403, detail="Access denied to this file")
            
    add_log("FILE_DOWNLOADED", current_user["username"], f"Downloaded file: {safe_filename}")
    return FileResponse(file_path, filename=safe_filename)
