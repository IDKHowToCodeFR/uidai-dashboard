import os
import io
import base64
import pandas as pd
from datetime import datetime
from typing import List, Optional
from functools import lru_cache
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from backend.api.auth_utils import (
    load_users, verify_password, create_access_token, get_current_user,
    add_user, remove_user, update_permissions, BASE_DIR, add_log, load_logs, archive_old_logs
)

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

PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    permissions: List[str]

class UserAddRequest(BaseModel):
    username: str
    password: str
    company_name: str
    permissions: Optional[List[str]] = None

class UserRemoveRequest(BaseModel):
    username: str

@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    users = load_users()
    user = users.get(form_data.username)
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    role = user["user"]
    permissions = user.get("permissions", [])
    access_token = create_access_token(data={"sub": form_data.username, "role": role, "permissions": permissions})
    add_log("LOGIN_SUCCESS", form_data.username, f"User {form_data.username} logged in successfully")
    return {"access_token": access_token, "token_type": "bearer", "role": role, "permissions": permissions}

@app.get("/users")
async def list_users(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return load_users()

@app.post("/users/add")
async def api_add_user(req: UserAddRequest, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    ok, msg = add_user(req.username, req.password, req.company_name, req.permissions)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@app.post("/users/remove")
async def api_remove_user(req: UserRemoveRequest, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    ok, msg = remove_user(req.username)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

class PermissionsRequest(BaseModel):
    username: str
    permissions: List[str]

@app.post("/users/permissions")
async def api_update_permissions(req: PermissionsRequest, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    ok, msg = update_permissions(req.username, req.permissions)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    user_role = current_user["role"]
    permissions = current_user.get("permissions", [])
    
    if user_role == "Admin":
        raise HTTPException(status_code=403, detail="Admins are not allowed to upload files.")
    if "can_upload_files" not in permissions:
        raise HTTPException(status_code=403, detail="You do not have permission to upload files.")
        
    prefix = f"{user_role}_" if user_role and user_role != 'Admin' else "Admin_"
    # Prevent path traversal
    safe_filename = os.path.basename(file.filename)
    out_filename = prefix + os.path.splitext(safe_filename)[0] + "_processed.csv"
    save_path = os.path.abspath(os.path.join(PROCESSED_DATA_DIR, out_filename))
    
    # Ensure save path is strictly within PROCESSED_DATA_DIR
    if not save_path.startswith(os.path.abspath(PROCESSED_DATA_DIR)):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    
    contents = await file.read()
    
    # Strictly validate content limits (e.g. max 50MB, simple check)
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
        
    try:
        if safe_filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        elif safe_filename.endswith('.xls') or safe_filename.endswith('.xlsx'):
            excel_file = pd.ExcelFile(io.BytesIO(contents), engine='openpyxl')
            dfs = []
            for sheet_name in excel_file.sheet_names:
                sheet_df = pd.read_excel(excel_file, sheet_name=sheet_name)
                if 'Company' not in sheet_df.columns:
                    sheet_df['Company'] = sheet_name
                dfs.append(sheet_df)
            df = pd.concat(dfs, ignore_index=True)
        else:
            raise HTTPException(status_code=400, detail="Invalid file type. Must be csv or excel.")
            
        numeric_cols = df.select_dtypes(include='number').columns
        df[numeric_cols] = df[numeric_cols].fillna(0)
        object_cols = df.select_dtypes(include=['object', 'string']).columns
        df[object_cols] = df[object_cols].fillna('Unknown')
        for col in object_cols:
            df[col] = df[col].astype(str).str.strip()
        df.dropna(how='all', inplace=True)
        df.dropna(axis=1, how='all', inplace=True)
        
        df.to_csv(save_path, index=False)
        add_log("FILE_UPLOADED", current_user["username"], f"Uploaded file: {out_filename}")
        return df.to_dict('records')
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history")
async def get_history(current_user: dict = Depends(get_current_user)):
    user_role = current_user["role"]
    permissions = current_user.get("permissions", [])
    
    if not os.path.exists(PROCESSED_DATA_DIR):
        return []
    
    files = [f for f in os.listdir(PROCESSED_DATA_DIR) if f.endswith('.csv')]
    
    if user_role != 'Admin' and 'can_view_global' not in permissions:
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

@app.get("/logs")
async def get_system_logs(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    logs = load_logs()
    logs.sort(key=lambda x: x['timestamp'], reverse=True)
    return logs

@lru_cache(maxsize=32)
def load_data_cached(file_path: str, mtime: float):
    # mtime is passed just to invalidate cache when file changes
    df = pd.read_csv(file_path)
    return df.to_dict('records')

@app.get("/data/aggregate")
async def get_aggregated_data(current_user: dict = Depends(get_current_user)):
    user_role = current_user["role"]
    permissions = current_user.get("permissions", [])
    if user_role != 'Admin' and 'can_view_global' not in permissions:
        raise HTTPException(status_code=403, detail="Global view denied")
        
    all_data = []
    if not os.path.exists(PROCESSED_DATA_DIR):
        return all_data
        
    for filename in os.listdir(PROCESSED_DATA_DIR):
        if filename.endswith(".csv"):
            file_path = os.path.join(PROCESSED_DATA_DIR, filename)
            mtime = os.path.getmtime(file_path)
            data = load_data_cached(file_path, mtime)
            # Add company based on filename if possible, but Dashboard relies on 'Company' column
            all_data.extend(data)
            
    return all_data

@app.get("/data/{filename}")
async def get_data(filename: str, current_user: dict = Depends(get_current_user)):
    user_role = current_user["role"]
    permissions = current_user.get("permissions", [])
    
    # Path traversal protection
    safe_filename = os.path.basename(filename)
    file_path = os.path.abspath(os.path.join(PROCESSED_DATA_DIR, safe_filename))
    
    if not file_path.startswith(os.path.abspath(PROCESSED_DATA_DIR)):
        raise HTTPException(status_code=400, detail="Invalid filename")
        
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    if user_role != 'Admin' and 'can_view_global' not in permissions:
        if 'can_view_scoped' not in permissions or not safe_filename.startswith(f"{user_role}_"):
            raise HTTPException(status_code=403, detail="Access denied to this file")
        
    mtime = os.path.getmtime(file_path)
    data = load_data_cached(file_path, mtime)
    return data

@app.get("/download/{filename}")
async def download_file(filename: str, current_user: dict = Depends(get_current_user)):
    user_role = current_user["role"]
    permissions = current_user.get("permissions", [])
    
    safe_filename = os.path.basename(filename)
    file_path = os.path.abspath(os.path.join(PROCESSED_DATA_DIR, safe_filename))
    
    if not file_path.startswith(os.path.abspath(PROCESSED_DATA_DIR)):
        raise HTTPException(status_code=400, detail="Invalid filename")
        
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    if user_role != 'Admin' and 'can_download_files' not in permissions:
        raise HTTPException(status_code=403, detail="Download permission denied")
        
    if user_role != 'Admin' and 'can_view_global' not in permissions:
        if 'can_view_scoped' not in permissions or not safe_filename.startswith(f"{user_role}_"):
            raise HTTPException(status_code=403, detail="Access denied to this file")
            
    add_log("FILE_DOWNLOADED", current_user["username"], f"Downloaded file: {safe_filename}")
    return FileResponse(file_path, filename=safe_filename)
