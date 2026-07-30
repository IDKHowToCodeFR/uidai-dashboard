import os
import json
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

DEFAULT_USERS = {
    "admin": {"password": "$2b$12$X50DPJYJecw2eYXRyNSoEeVXKBoB0cI81Wu6zDEAEYBrz07/pw4We", "user": "Admin", "permissions": []},
    "uidai": {"password": "$2b$12$aUSO1G0HFd65c9qjV8oS8OGBMAtimCzgN.Jet95k6sQAp6IHtc9xC", "user": "UIDAI", "permissions": ["can_view_global"]},
    "digitech": {"password": "$2b$12$GgpVm1yfX3UkVNZy86x1luuJExeT4Gydg4zqKE7AVnkyXYL4y5eWu", "user": "Digitech", "permissions": ["can_view_scoped", "can_upload_files"]},
    "nsb": {"password": "$2b$12$YGSWt0yqjviML6HVAcqqyO6OJ97ha3OA0gal/e7F4WhAkKJii2boy", "user": "NSB", "permissions": ["can_view_scoped", "can_upload_files"]},
}

LOGS_FILE = os.path.join(BASE_DIR, 'data', 'logs.json')

def load_logs():
    if os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, 'r') as f:
            return json.load(f)
    return []

def add_log(action: str, username: str, details: str = ""):
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

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    save_users(DEFAULT_USERS)
    return DEFAULT_USERS.copy()

def save_users(users):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def add_user(username, password, company_name, permissions=None):
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
    users = load_users()
    key = username.lower().strip()
    if key not in users:
        return False, "User not found."
    users[key]["permissions"] = permissions
    save_users(users)
    add_log("PERMISSIONS_UPDATED", "Admin", f"Updated permissions for '{username}': {permissions}")
    return True, f"Permissions updated for '{username}'."

def remove_user(username):
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
