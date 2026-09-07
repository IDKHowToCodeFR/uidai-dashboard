from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database.database import get_db
from backend.database.models import User
from backend.auth.auth_utils import (
    load_users, verify_and_upgrade_password, create_access_token, create_refresh_token, get_current_user,
    add_user, remove_user, update_permissions, record_login, reset_password, require_permission
)
from backend.audit.audit_logger import add_log, extract_request_metadata

router = APIRouter()

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    role: str
    permissions: List[str]
    companies: List[str]

class RefreshRequest(BaseModel):
    refresh_token: str

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
    companies: Optional[List[str]] = None
    data_lookback_days: Optional[int] = None

class ResetPasswordRequest(BaseModel):
    username: str
    new_password: str

class PageViewRequest(BaseModel):
    pathname: str

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
    
    if role == "Admin":
        from backend.auth.auth_utils import get_admin_permissions
        permissions = get_admin_permissions()
    else:
        permissions = [p.permission_name for p in db_user.permissions] if db_user.permissions else []
    
    # We only need the 'sub' claim now as get_current_user checks the DB dynamically.
    access_token = create_access_token(data={"sub": form_data.username})
    refresh_token = create_refresh_token(data={"sub": form_data.username})
    
    record_login(db, form_data.username)
    meta = extract_request_metadata(request)
    add_log(db, "LOGIN_SUCCESS", form_data.username, f"User {form_data.username} logged in successfully", **meta)
    
    # Return role/permissions/companies for the frontend's initial state
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer", 
        "role": role, 
        "permissions": permissions, 
        "companies": companies
    }

@router.post("/refresh", response_model=Token)
async def refresh_token(req: RefreshRequest, db: Session = Depends(get_db)):
    from jose import jwt, JWTError
    from backend.auth.auth_utils import SECRET_KEY, ALGORITHM
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
    )
    try:
        payload = jwt.decode(req.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        if username is None or token_type != "refresh":
            raise credentials_exception
            
        db_user = db.query(User).filter(User.username == username).first()
        if not db_user:
            raise credentials_exception
            
        companies = db_user.companies or []
        role = "Admin" if "Admin" in companies or username.lower() == "admin" else "User"
        
        if role == "Admin":
            from backend.auth.auth_utils import get_admin_permissions
            permissions = get_admin_permissions()
        else:
            permissions = [p.permission_name for p in db_user.permissions] if db_user.permissions else []
        
        access_token = create_access_token(data={"sub": username})
        new_refresh_token = create_refresh_token(data={"sub": username})
        
        return {
            "access_token": access_token, 
            "refresh_token": new_refresh_token,
            "token_type": "bearer", 
            "role": role, 
            "permissions": permissions, 
            "companies": companies
        }
    except JWTError:
        raise credentials_exception

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    return {"message": "Successfully logged out"}

@router.get("/users")
async def list_users(current_user: dict = Depends(require_permission('can_manage_users')), db: Session = Depends(get_db)):
    return load_users(db, current_user)

@router.post("/users/add")
async def add_new_user(request: Request, req: UserAddRequest, current_user: dict = Depends(require_permission('can_manage_users')), db: Session = Depends(get_db)):
    meta = extract_request_metadata(request)
    success, msg = add_user(db, req.username, req.password, req.companies, req.permissions, actor=current_user.get("username", "Unknown"), **meta)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@router.post("/users/remove")
async def api_remove_user(request: Request, req: UserRemoveRequest, current_user: dict = Depends(require_permission('can_manage_users')), db: Session = Depends(get_db)):
    meta = extract_request_metadata(request)
    ok, msg = remove_user(db, req.username, actor=current_user.get("username", "Unknown"), **meta)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@router.post("/users/permissions")
async def api_update_permissions(request: Request, req: PermissionsRequest, current_user: dict = Depends(require_permission('can_manage_users')), db: Session = Depends(get_db)):
    meta = extract_request_metadata(request)
    ok, msg = update_permissions(db, req.username, req.permissions, req.companies, req.data_lookback_days, actor=current_user.get("username", "Unknown"), **meta)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@router.post("/users/reset-password")
async def api_reset_password(request: Request, req: ResetPasswordRequest, current_user: dict = Depends(require_permission('can_manage_users')), db: Session = Depends(get_db)):
    meta = extract_request_metadata(request)
    ok, msg = reset_password(db, req.username, req.new_password, actor=current_user.get("username", "Unknown"), **meta)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@router.post("/logs/page_view")
async def api_log_page_view(request: Request, req: PageViewRequest, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    meta = extract_request_metadata(request)
    add_log(db, "PAGE_VIEW", current_user.get("username", "Unknown"), f"Viewed {req.pathname}", **meta)
    return {"message": "Logged"}
