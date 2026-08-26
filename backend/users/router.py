from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database.database import get_db
from backend.database.models import User
from backend.auth.auth_utils import (
    load_users, verify_and_upgrade_password, create_access_token, get_current_user,
    add_user, remove_user, update_permissions, add_log, record_login, reset_password, extract_request_metadata
)

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    permissions: List[str]
    companies: List[str]

class UserAddRequest(BaseModel):
    username: str
    password: str
    companies: List[str]
    permissions: Optional[List[str]] = None

class UserRemoveRequest(BaseModel):
    username: str

class PermissionsRequest(BaseModel):
    username: str
    permissions: List[str]

class ResetPasswordRequest(BaseModel):
    username: str
    new_password: str

@router.post("/login", response_model=Token)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    key = form_data.username.lower().strip()
    db_user = db.query(User).filter(User.username == key).first()
    
    if not db_user or not verify_and_upgrade_password(db, db_user, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    companies = db_user.companies or []
    role = "Admin" if "Admin" in companies or key == "admin" else "User"
    
    # We still need permissions to generate the token, we can get them from db_user.permissions
    permissions = [p.permission_name for p in db_user.permissions] if db_user.permissions else []
    
    # We still pass 'role' for frontend backward compatibility, and add 'companies' for data filtering
    access_token = create_access_token(data={
        "sub": form_data.username, 
        "role": role, 
        "permissions": permissions,
        "companies": companies
    })
    record_login(db, form_data.username)
    meta = extract_request_metadata(request)
    add_log(db, "LOGIN_SUCCESS", form_data.username, f"User {form_data.username} logged in successfully", **meta)
    return {"access_token": access_token, "token_type": "bearer", "role": role, "permissions": permissions, "companies": companies}

@router.get("/users")
async def list_users(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return load_users(db)

@router.post("/users/add")
async def add_new_user(request: Request, req: UserAddRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    meta = extract_request_metadata(request)
    success, msg = add_user(db, req.username, req.password, req.companies, req.permissions, **meta)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@router.post("/users/remove")
async def api_remove_user(request: Request, req: UserRemoveRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    meta = extract_request_metadata(request)
    ok, msg = remove_user(db, req.username, **meta)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@router.post("/users/permissions")
async def api_update_permissions(request: Request, req: PermissionsRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    meta = extract_request_metadata(request)
    ok, msg = update_permissions(db, req.username, req.permissions, **meta)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@router.post("/users/reset-password")
async def api_reset_password(request: Request, req: ResetPasswordRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    meta = extract_request_metadata(request)
    ok, msg = reset_password(db, req.username, req.new_password, **meta)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}
