from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database.database import get_db
from backend.auth.auth_utils import (
    load_users, verify_password, create_access_token, get_current_user,
    add_user, remove_user, update_permissions, add_log, record_login, reset_password
)

router = APIRouter()

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

class PermissionsRequest(BaseModel):
    username: str
    permissions: List[str]

class ResetPasswordRequest(BaseModel):
    username: str
    new_password: str

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    users = load_users(db)
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
    record_login(db, form_data.username)
    add_log(db, "LOGIN_SUCCESS", form_data.username, f"User {form_data.username} logged in successfully")
    return {"access_token": access_token, "token_type": "bearer", "role": role, "permissions": permissions}

@router.get("/users")
async def list_users(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return load_users(db)

@router.post("/users/add")
async def api_add_user(req: UserAddRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    ok, msg = add_user(db, req.username, req.password, req.company_name, req.permissions)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@router.post("/users/remove")
async def api_remove_user(req: UserRemoveRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    ok, msg = remove_user(db, req.username)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@router.post("/users/permissions")
async def api_update_permissions(req: PermissionsRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    ok, msg = update_permissions(db, req.username, req.permissions)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@router.post("/users/reset-password")
async def api_reset_password(req: ResetPasswordRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    ok, msg = reset_password(db, req.username, req.new_password)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}
