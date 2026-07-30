import os
import io
import base64
import pandas as pd
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from backend.api.auth_utils import (
    load_users, verify_password, create_access_token, get_current_user,
    add_user, remove_user, BASE_DIR
)

app = FastAPI(title="UIDAI Backend API")

PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

class UserAddRequest(BaseModel):
    username: str
    password: str
    company_name: str

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
    access_token = create_access_token(data={"sub": form_data.username, "role": role})
    return {"access_token": access_token, "token_type": "bearer", "role": role}

@app.get("/users")
async def list_users(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return load_users()

@app.post("/users/add")
async def api_add_user(req: UserAddRequest, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    ok, msg = add_user(req.username, req.password, req.company_name)
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

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    user_role = current_user["role"]
    prefix = f"{user_role}_" if user_role and user_role != 'Admin' else "Admin_"
    filename = file.filename
    out_filename = prefix + os.path.splitext(filename)[0] + "_processed.csv"
    save_path = os.path.join(PROCESSED_DATA_DIR, out_filename)
    
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    
    contents = await file.read()
    
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        elif filename.endswith('.xls') or filename.endswith('.xlsx'):
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
        return df.to_dict('records')
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history(current_user: dict = Depends(get_current_user)):
    user_role = current_user["role"]
    if not os.path.exists(PROCESSED_DATA_DIR):
        return []
    
    files = [f for f in os.listdir(PROCESSED_DATA_DIR) if f.endswith('.csv')]
    if user_role and user_role != 'Admin':
        prefix = f"{user_role}_"
        files = [f for f in files if f.startswith(prefix)]

    file_times = []
    for f in files:
        file_path = os.path.join(PROCESSED_DATA_DIR, f)
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        file_times.append({'name': f, 'time': mtime.isoformat()})
    
    file_times.sort(key=lambda x: x['time'], reverse=True)
    return file_times

@app.get("/data/{filename}")
async def get_data(filename: str, current_user: dict = Depends(get_current_user)):
    user_role = current_user["role"]
    file_path = os.path.join(PROCESSED_DATA_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    # Security check: User can only access their own files unless Admin
    if user_role != 'Admin' and not filename.startswith(f"{user_role}_"):
        raise HTTPException(status_code=403, detail="Access denied to this file")
        
    df = pd.read_csv(file_path)
    return df.to_dict('records')
