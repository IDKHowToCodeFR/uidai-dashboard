import os
import json
import threading
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import bcrypt
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey_change_me_in_production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 day

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Path to the data dir (one level up from api)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_FILE = os.path.join(BASE_DIR, 'data', 'users.json')

# Global database lock to prevent race conditions when reading/writing JSON files
db_lock = threading.RLock()

DEFAULT_USERS = {
    "admin": {"password": "$2b$12$X50DPJYJecw2eYXRyNSoEeVXKBoB0cI81Wu6zDEAEYBrz07/pw4We", "user": "Admin", "permissions": ["can_view_global", "can_view_scoped", "can_upload_files", "can_download_files"]},
    "uidai": {"password": "$2b$12$aUSO1G0HFd65c9qjV8oS8OGBMAtimCzgN.Jet95k6sQAp6IHtc9xC", "user": "UIDAI", "permissions": ["can_view_global"]},
    "digitech": {"password": "$2b$12$GgpVm1yfX3UkVNZy86x1luuJExeT4Gydg4zqKE7AVnkyXYL4y5eWu", "user": "Digitech", "permissions": ["can_view_scoped", "can_upload_files"]},
    "nsb": {"password": "$2b$12$YGSWt0yqjviML6HVAcqqyO6OJ97ha3OA0gal/e7F4WhAkKJii2boy", "user": "NSB", "permissions": ["can_view_scoped", "can_upload_files"]},
}

LOGS_FILE = os.path.join(BASE_DIR, 'data', 'logs.json')
SETTINGS_FILE = os.path.join(BASE_DIR, 'data', 'settings.json')

DEFAULT_SETTINGS = {
    "radar_sla_targets": [85, 95, 95, 85, 85, 85]
}

def load_settings():
    with db_lock:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    with db_lock:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)

def load_logs():
    with db_lock:
        if os.path.exists(LOGS_FILE):
            with open(LOGS_FILE, 'r') as f:
                return json.load(f)
        return []

def add_log(action: str, username: str, details: str = ""):
    with db_lock:
        logs = load_logs()
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "username": username,
            "details": details
        }
        logs.append(log_entry)
        os.makedirs(os.path.dirname(LOGS_FILE), exist_ok=True)
        with open(LOGS_FILE, 'w') as f:
            json.dump(logs, f, indent=2)

def archive_old_logs(days=90):
    with db_lock:
        logs = load_logs()
        if not logs:
            return
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_logs = []
        archived_logs = []
        
        for log in logs:
            try:
                log_date = datetime.fromisoformat(log.get("timestamp", ""))
                if log_date < cutoff_date:
                    archived_logs.append(log)
                else:
                    recent_logs.append(log)
            except Exception:
                recent_logs.append(log)
                
        if archived_logs:
            archive_filename = f"logs_archive_{datetime.now().strftime('%Y_%m')}.json"
            archive_path = os.path.join(os.path.dirname(LOGS_FILE), archive_filename)
            
            existing_archive = []
            if os.path.exists(archive_path):
                try:
                    with open(archive_path, 'r') as f:
                        existing_archive = json.load(f)
                except Exception:
                    pass
                    
            existing_archive.extend(archived_logs)
            
            with open(archive_path, 'w') as f:
                json.dump(existing_archive, f, indent=2)
                
            with open(LOGS_FILE, 'w') as f:
                json.dump(recent_logs, f, indent=2)

def load_users():
    with db_lock:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                users = json.load(f)
                # Migration: Ensure existing admin has proper permissions
                if "admin" in users and not users["admin"].get("permissions"):
                    users["admin"]["permissions"] = ["can_view_global", "can_view_scoped", "can_upload_files", "can_download_files"]
                    save_users(users)
                return users
        save_users(DEFAULT_USERS)
        return DEFAULT_USERS.copy()

def save_users(users):
    with db_lock:
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)

def add_user(username, password, company_name, permissions=None):
    with db_lock:
        if permissions is None:
            permissions = []
        users = load_users()
        key = username.lower().strip()
        if key in users:
            return False, "Username already exists."
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        users[key] = {"password": hashed_password, "user": company_name, "permissions": permissions}
        save_users(users)
        add_log("USER_ADDED", "Admin", f"Added company '{company_name}' ({username}) with perms {permissions}")
        return True, f"Company '{company_name}' added."

def update_permissions(username, permissions):
    with db_lock:
        users = load_users()
        key = username.lower().strip()
        if key not in users:
            return False, "User not found."
        users[key]["permissions"] = permissions
        save_users(users)
        add_log("PERMISSIONS_UPDATED", "Admin", f"Updated permissions for '{username}': {permissions}")
        return True, f"Permissions updated for '{username}'."

def reset_password(username, new_password):
    with db_lock:
        users = load_users()
        key = username.lower().strip()
        if key not in users:
            return False, "User not found."
        
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        users[key]["password"] = hashed_password
        save_users(users)
        add_log("PASSWORD_RESET", "Admin", f"Reset password for '{username}'")
        return True, f"Password reset for '{username}'."

def remove_user(username):
    with db_lock:
        users = load_users()
        key = username.lower().strip()
        if key not in users:
            return False, "Company not found."
        if users[key].get("user") == "Admin":
            return False, "Cannot remove an Admin account."
        company_name = users[key].get("user", key)
        del users[key]
        save_users(users)
        add_log("USER_DEACTIVATED", "Admin", f"Deactivated account for '{company_name}' ({username})")
        return True, f"Account for '{company_name}' deactivated."

def verify_password(plain_password, stored_password):
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

def record_login(username):
    with db_lock:
        users = load_users()
        key = username.lower().strip()
        if key in users:
            users[key]['login_count'] = users[key].get('login_count', 0) + 1
            users[key]['last_login'] = datetime.now().isoformat()
            save_users(users)
