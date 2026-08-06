import os
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException, status, Security, Depends
from fastapi.security import OAuth2PasswordBearer
import bcrypt
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import delete
from typing import List, Dict

from backend.api.database import get_db
from backend.api.models import User, UserPermission, AuditLog, Setting

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey_change_me_in_production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 day

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

DEFAULT_SETTINGS = {
    "radar_sla_targets": [85, 95, 95, 85, 85, 85]
}

def load_settings(db: Session) -> dict:
    settings = db.query(Setting).all()
    if not settings:
        return DEFAULT_SETTINGS.copy()
    return {s.key: s.value for s in settings}

def save_settings(db: Session, settings: dict):
    for k, v in settings.items():
        setting = db.query(Setting).filter(Setting.key == k).first()
        if setting:
            setting.value = v
        else:
            setting = Setting(key=k, value=v)
            db.add(setting)
    db.commit()

def load_logs(db: Session) -> List[dict]:
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).all()
    return [{"timestamp": l.timestamp, "action": l.action, "username": l.username, "details": l.details} for l in logs]

def add_log(db: Session, action: str, username: str, details: str = ""):
    log_entry = AuditLog(
        timestamp=datetime.now().isoformat(),
        action=action,
        username=username,
        details=details
    )
    db.add(log_entry)
    db.commit()

def archive_old_logs(db: Session, days=90):
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
    # For a robust solution, we could move these to a cold storage DB/file. 
    # For now, we will simply delete them from the active table to save space.
    db.query(AuditLog).filter(AuditLog.timestamp < cutoff_date).delete()
    db.commit()

def load_users(db: Session) -> dict:
    users = db.query(User).all()
    result = {}
    for user in users:
        permissions = [p.permission_name for p in user.permissions]
        result[user.username] = {
            "password": user.password_hash,
            "user": user.company_name,
            "permissions": permissions,
            "login_count": user.login_count,
            "last_login": user.last_login
        }
    return result

def add_user(db: Session, username: str, password: str, company_name: str, permissions: list = None):
    if permissions is None:
        permissions = []
    
    key = username.lower().strip()
    existing = db.query(User).filter(User.username == key).first()
    if existing:
        return False, "Username already exists."
    
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    new_user = User(
        username=key,
        password_hash=hashed_password,
        company_name=company_name
    )
    db.add(new_user)
    db.flush() # To get the new_user.id
    
    for p in permissions:
        db.add(UserPermission(user_id=new_user.id, permission_name=p))
        
    db.commit()
    add_log(db, "USER_ADDED", "Admin", f"Added company '{company_name}' ({username}) with perms {permissions}")
    return True, f"Company '{company_name}' added."

def update_permissions(db: Session, username: str, permissions: list):
    key = username.lower().strip()
    user = db.query(User).filter(User.username == key).first()
    if not user:
        return False, "User not found."
    
    # Delete existing permissions
    db.query(UserPermission).filter(UserPermission.user_id == user.id).delete()
    
    # Add new permissions
    for p in permissions:
        db.add(UserPermission(user_id=user.id, permission_name=p))
        
    db.commit()
    add_log(db, "PERMISSIONS_UPDATED", "Admin", f"Updated permissions for '{username}': {permissions}")
    return True, f"Permissions updated for '{username}'."

def reset_password(db: Session, username: str, new_password: str):
    key = username.lower().strip()
    user = db.query(User).filter(User.username == key).first()
    if not user:
        return False, "User not found."
    
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user.password_hash = hashed_password
    db.commit()
    add_log(db, "PASSWORD_RESET", "Admin", f"Reset password for '{username}'")
    return True, f"Password reset for '{username}'."

def remove_user(db: Session, username: str):
    key = username.lower().strip()
    user = db.query(User).filter(User.username == key).first()
    if not user:
        return False, "Company not found."
    if user.company_name == "Admin":
        return False, "Cannot remove an Admin account."
    
    company_name = user.company_name
    db.delete(user)
    db.commit()
    add_log(db, "USER_DEACTIVATED", "Admin", f"Deactivated account for '{company_name}' ({username})")
    return True, f"Account for '{company_name}' deactivated."

def verify_password(plain_password: str, stored_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), stored_password.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Security(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        permissions: list = payload.get("permissions", [])
        if username is None or role is None:
            raise credentials_exception
        return {"username": username, "role": role, "permissions": permissions}
    except JWTError:
        raise credentials_exception

class PermissionChecker:
    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(self, current_user: dict = Security(get_current_user)):
        permissions = current_user.get("permissions", [])
        if self.required_permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires permission: {self.required_permission}"
            )
        return current_user

def record_login(db: Session, username: str):
    key = username.lower().strip()
    user = db.query(User).filter(User.username == key).first()
    if user:
        user.login_count = (user.login_count or 0) + 1
        user.last_login = datetime.now().isoformat()
        db.commit()
