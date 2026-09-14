import os
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from fastapi import HTTPException, status, Security, Depends, Request, WebSocket
from fastapi.security import OAuth2PasswordBearer
import bcrypt
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import delete
from typing import List, Dict

from backend.database.database import get_db
from backend.database.models import User, UserPermission, AuditLog, Setting
from backend.audit.audit_logger import add_log, extract_request_metadata

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey_change_me_in_production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7 # 7 days
SERVER_START_TIME = int(datetime.now(timezone.utc).timestamp())

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except ValueError:
        return False

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def load_users(db: Session, current_user: dict = None) -> dict:
    users = db.query(User).all()
    result = {}
    
    is_superadmin = False
    admin_companies = []
    if current_user:
        is_superadmin = current_user.get("username", "").lower() == "admin"
        admin_companies = current_user.get("companies", [])
        
    for user in users:
        permissions_obj = user.permissions
        
        is_admin = permissions_obj.is_admin if permissions_obj else False
        lookback = permissions_obj.data_lookback_days if permissions_obj else None
        
        user_companies = ["Admin"] if is_admin else []
        permissions = []
        if permissions_obj:
            if permissions_obj.company_digitech: user_companies.append("Digitech")
            if user.permissions.company_nsb: user_companies.append("NSB")
            if user.permissions.can_view_ccf: permissions.append("can_view_ccf")
            if user.permissions.can_view_unimate: permissions.append("can_view_unimate")
            if user.permissions.can_view_cdr: permissions.append("can_view_cdr")
            if user.permissions.can_view_apr: permissions.append("can_view_apr")
            if user.permissions.can_download_files: permissions.append("can_download_files")
            
        if current_user and not is_superadmin:
            if user.username.lower() != current_user.get("username", "").lower():
                if not any(c in admin_companies for c in user_companies):
                    continue
                    
        result[user.username] = {
            "password": user.password_hash,
            "companies": user_companies,
            "permissions": permissions,
            "login_count": user.login_count,
            "last_login": user.last_login,
            "data_lookback_days": lookback
        }
    return result

def add_user(db: Session, username: str, password: str, companies: list, permissions: list = None, actor: str = "Admin", ip_address: str = None, user_agent: str = None, endpoint: str = None):
    if permissions is None:
        permissions = []
    
    key = username.lower().strip()
    existing = db.query(User).filter(User.username == key).first()
    if existing:
        return False, "Username already exists."
    
    hashed_password = get_password_hash(password)
    new_user = User(
        username=key,
        password_hash=hashed_password
    )
    db.add(new_user)
    db.flush() # To get the new_user.id
    
    db.add(UserPermission(
        user_id=new_user.id,
        is_admin="Admin" in companies,
        data_lookback_days=None,
        company_digitech="Digitech" in companies,
        company_nsb="NSB" in companies,
        can_view_ccf="can_view_ccf" in permissions,
        can_view_unimate="can_view_unimate" in permissions,
        can_view_cdr="can_view_cdr" in permissions,
        can_view_apr="can_view_apr" in permissions,
        can_download_files="can_download_files" in permissions
    ))
        
    db.commit()
    add_log(db, "USER_ADDED", actor, f"Added user '{username}' with companies {companies} and perms {permissions}", ip_address=ip_address, user_agent=user_agent, endpoint=endpoint)
    return True, f"User '{username}' added."

def update_permissions(db: Session, username: str, permissions: list, companies: list = None, data_lookback_days: int = None, actor: str = "Admin", ip_address: str = None, user_agent: str = None, endpoint: str = None):
    key = username.lower().strip()
    user = db.query(User).filter(User.username == key).first()
    if not user:
        return False, "User not found."
        
    if key == "admin":
        return False, "Cannot modify admin permissions."
    
    is_admin = False
    if user.permissions:
        is_admin = user.permissions.is_admin
        
    if companies is not None:
        is_admin = "Admin" in companies
        
    # Delete existing permissions
    db.query(UserPermission).filter(UserPermission.user_id == user.id).delete()
    
    # Add new permissions
    db.add(UserPermission(
        user_id=user.id,
        is_admin=is_admin,
        data_lookback_days=data_lookback_days,
        company_digitech="Digitech" in (companies or []),
        company_nsb="NSB" in (companies or []),
        can_view_ccf="can_view_ccf" in permissions,
        can_view_unimate="can_view_unimate" in permissions,
        can_view_cdr="can_view_cdr" in permissions,
        can_view_apr="can_view_apr" in permissions,
        can_download_files="can_download_files" in permissions
    ))
        
    db.commit()
    add_log(db, "PERMISSIONS_UPDATED", actor, f"Updated permissions & companies for '{username}'", ip_address=ip_address, user_agent=user_agent, endpoint=endpoint)
    return True, f"Permissions & companies updated for '{username}'."

def reset_password(db: Session, username: str, new_password: str, actor: str = "Admin", ip_address: str = None, user_agent: str = None, endpoint: str = None):
    key = username.lower().strip()
    user = db.query(User).filter(User.username == key).first()
    if not user:
        return False, "User not found."
    
    hashed_password = get_password_hash(new_password)
    user.password_hash = hashed_password
    db.commit()
    add_log(db, "PASSWORD_RESET", actor, f"Reset password for '{username}'", ip_address=ip_address, user_agent=user_agent, endpoint=endpoint)
    return True, f"Password reset for '{username}'."

def remove_user(db: Session, username: str, actor: str = "Admin", ip_address: str = None, user_agent: str = None, endpoint: str = None):
    key = username.lower().strip()
    user = db.query(User).filter(User.username == key).first()
    if not user:
        return False, "User not found."
        
    is_admin = user.permissions.is_admin if user.permissions else False
    if is_admin or key == "admin":
        return False, "Cannot remove an Admin account."
    
    db.delete(user)
    db.commit()
    add_log(db, "USER_DEACTIVATED", actor, f"Deactivated account for ({username})", ip_address=ip_address, user_agent=user_agent, endpoint=endpoint)
    return True, f"Account for '{username}' deactivated."

def verify_and_upgrade_password(db: Session, db_user: User, plain_password: str) -> bool:
    return verify_password(plain_password, db_user.password_hash)

def get_admin_permissions():
    return [
        "can_download_files", "can_view_global",
        "can_view_ccf", "can_view_unimate", "can_view_cdr", "can_view_apr",
        "can_manage_users", "can_view_logs", "can_edit_settings"
    ]

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access", "iat": int(datetime.now(timezone.utc).timestamp())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "iat": int(datetime.now(timezone.utc).timestamp())})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
    
async def get_current_user(token: str = Security(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        token_type: str = payload.get("type")
        iat = payload.get("iat")
        
        if username is None or token_type != "access":
            raise credentials_exception
            
        if iat is None or iat < SERVER_START_TIME:
            raise credentials_exception
            
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise credentials_exception
            
        permissions_obj = user.permissions
        is_admin = permissions_obj.is_admin if permissions_obj else False
        lookback = permissions_obj.data_lookback_days if permissions_obj else None
            
        role = "Admin" if is_admin or username.lower() == "admin" else "User"
        
        user_companies = ["Admin"] if role == "Admin" else []
        permissions = []
        
        if permissions_obj:
            if permissions_obj.company_digitech: user_companies.append("Digitech")
            if permissions_obj.company_nsb: user_companies.append("NSB")
            if permissions_obj.can_view_ccf: permissions.append("can_view_ccf")
            if permissions_obj.can_view_unimate: permissions.append("can_view_unimate")
            if permissions_obj.can_view_cdr: permissions.append("can_view_cdr")
            if permissions_obj.can_view_apr: permissions.append("can_view_apr")
            if permissions_obj.can_download_files: permissions.append("can_download_files")
        
        if role == "Admin":
            permissions = get_admin_permissions()
        
        return {"username": user.username, "role": role, "permissions": permissions, "companies": user_companies, "data_lookback_days": lookback}
    except JWTError:
        raise credentials_exception

def require_permission(required_permission: str):
    def checker(request: Request, current_user: dict = Security(get_current_user), db: Session = Depends(get_db)):
        permissions = current_user.get("permissions", [])
        if required_permission not in permissions:
            meta = extract_request_metadata(request)
            add_log(db, "UNAUTHORIZED_ACCESS", current_user.get("username", "Unknown"), f"Attempted to access endpoint requiring {required_permission}", **meta)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires permission: {required_permission}"
            )
        return current_user
    return checker

def record_login(db: Session, username: str):
    key = username.lower().strip()
    user = db.query(User).filter(User.username == key).first()
    if user:
        user.login_count = (user.login_count or 0) + 1
        user.last_login = datetime.now().isoformat()
        db.commit()
