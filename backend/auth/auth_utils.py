import os
from datetime import datetime, timedelta
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
        if current_user and not is_superadmin:
            user_companies = user.companies or []
            if user.username.lower() != current_user.get("username", "").lower():
                if not any(c in admin_companies for c in user_companies):
                    continue
                    
        permissions = [p.permission_name for p in user.permissions]
        result[user.username] = {
            "password": user.password_hash,
            "companies": user.companies,
            "permissions": permissions,
            "login_count": user.login_count,
            "last_login": user.last_login
        }
    return result

def add_user(db: Session, username: str, password: str, companies: list, permissions: list = None, ip_address: str = None, user_agent: str = None, endpoint: str = None):
    if permissions is None:
        permissions = []
    
    key = username.lower().strip()
    existing = db.query(User).filter(User.username == key).first()
    if existing:
        return False, "Username already exists."
    
    hashed_password = get_password_hash(password)
    new_user = User(
        username=key,
        password_hash=hashed_password,
        companies=companies
    )
    db.add(new_user)
    db.flush() # To get the new_user.id
    
    for p in permissions:
        db.add(UserPermission(user_id=new_user.id, permission_name=p))
        
    db.commit()
    add_log(db, "USER_ADDED", "Admin", f"Added user '{username}' with companies {companies} and perms {permissions}", ip_address=ip_address, user_agent=user_agent, endpoint=endpoint)
    return True, f"User '{username}' added."

def update_permissions(db: Session, username: str, permissions: list, companies: list = None, ip_address: str = None, user_agent: str = None, endpoint: str = None):
    key = username.lower().strip()
    user = db.query(User).filter(User.username == key).first()
    if not user:
        return False, "User not found."
        
    if key == "admin":
        return False, "Cannot modify admin permissions."
    
    if companies is not None:
        user.companies = companies
        
    # Delete existing permissions
    db.query(UserPermission).filter(UserPermission.user_id == user.id).delete()
    
    # Add new permissions
    for p in permissions:
        db.add(UserPermission(user_id=user.id, permission_name=p))
        
    db.commit()
    add_log(db, "PERMISSIONS_UPDATED", "Admin", f"Updated permissions & companies for '{username}'", ip_address=ip_address, user_agent=user_agent, endpoint=endpoint)
    return True, f"Permissions & companies updated for '{username}'."

def reset_password(db: Session, username: str, new_password: str, ip_address: str = None, user_agent: str = None, endpoint: str = None):
    key = username.lower().strip()
    user = db.query(User).filter(User.username == key).first()
    if not user:
        return False, "User not found."
    
    hashed_password = get_password_hash(new_password)
    user.password_hash = hashed_password
    db.commit()
    add_log(db, "PASSWORD_RESET", "Admin", f"Reset password for '{username}'", ip_address=ip_address, user_agent=user_agent, endpoint=endpoint)
    return True, f"Password reset for '{username}'."

def remove_user(db: Session, username: str, ip_address: str = None, user_agent: str = None, endpoint: str = None):
    key = username.lower().strip()
    user = db.query(User).filter(User.username == key).first()
    if not user:
        return False, "User not found."
    if "Admin" in user.companies or key == "admin":
        return False, "Cannot remove an Admin account."
    
    db.delete(user)
    db.commit()
    add_log(db, "USER_DEACTIVATED", "Admin", f"Deactivated account for ({username})", ip_address=ip_address, user_agent=user_agent, endpoint=endpoint)
    return True, f"Account for '{username}' deactivated."

def verify_and_upgrade_password(db: Session, db_user: User, plain_password: str) -> bool:
    return verify_password(plain_password, db_user.password_hash)

def get_admin_permissions():
    return [
        "can_download_files", 
        "can_view_ccf", 
        "can_view_unimate", "can_view_cdr", "can_view_apr",
        "can_manage_users", "can_view_logs", "can_edit_settings"
    ]

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
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
        
        if username is None or token_type != "access":
            raise credentials_exception
            
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise credentials_exception
            
        role = "Admin" if "Admin" in user.companies or username.lower() == "admin" else "User"
        
        if role == "Admin":
            permissions = get_admin_permissions()
        else:
            permissions = [p.permission_name for p in user.permissions]
        
        return {"username": user.username, "role": role, "permissions": permissions, "companies": user.companies}
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
