import os
import json
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

SECRET_KEY = "supersecretkey_change_me_in_production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 day

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Path to the data dir (one level up from api)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_FILE = os.path.join(BASE_DIR, 'data', 'users.json')

DEFAULT_USERS = {
    "admin": {"password": "admin", "user": "Admin"},
    "digitech": {"password": "digitech", "user": "Digitech"},
    "nsb": {"password": "nsb", "user": "NSB"},
}

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

def add_user(username, password, company_name):
    users = load_users()
    key = username.lower().strip()
    if key in users:
        return False, "Username already exists."
    users[key] = {"password": password, "user": company_name}
    save_users(users)
    return True, f"Company '{company_name}' added."

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
    return True, f"Company '{company_name}' removed."

def verify_password(plain_password, stored_password):
    return plain_password == stored_password

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
        if username is None or role is None:
            raise credentials_exception
        return {"username": username, "role": role}
    except JWTError:
        raise credentials_exception
