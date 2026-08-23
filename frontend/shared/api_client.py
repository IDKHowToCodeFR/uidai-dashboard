import requests
import base64
from functools import lru_cache
import pandas as pd
import os
from flask import request, has_request_context

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()

    def _get_headers(self, token: str = None):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
            
        if has_request_context():
            # Forward the true client IP from Dash frontend to FastAPI backend
            x_forwarded = request.headers.get("X-Forwarded-For")
            if x_forwarded:
                headers["X-Forwarded-For"] = x_forwarded
            elif request.remote_addr:
                headers["X-Real-IP"] = request.remote_addr
                
            # Forward User Agent
            user_agent = request.headers.get("User-Agent")
            if user_agent:
                headers["User-Agent"] = user_agent
                
        return headers

    def _handle_response(self, response):
        return response

    def login(self, username, password):
        return self._handle_response(self.session.post(
            f"{self.base_url}/login", 
            data={"username": username, "password": password},
            headers=self._get_headers()
        ))

    def get_users(self, token: str):
        return self._handle_response(self.session.get(f"{self.base_url}/users", headers=self._get_headers(token)))

    def add_user(self, token: str, req_data: dict):
        return self._handle_response(self.session.post(f"{self.base_url}/users/add", headers=self._get_headers(token), json=req_data))

    def remove_user(self, token: str, username: str):
        return self._handle_response(self.session.post(f"{self.base_url}/users/remove", headers=self._get_headers(token), json={"username": username}))

    def update_permissions(self, token: str, req_data: dict):
        return self._handle_response(self.session.post(f"{self.base_url}/users/permissions", headers=self._get_headers(token), json=req_data))

    def reset_password(self, token: str, req_data: dict):
        return self._handle_response(self.session.post(f"{self.base_url}/users/reset-password", headers=self._get_headers(token), json=req_data))

    def get_logs(self, token: str):
        return self._handle_response(self.session.get(f"{self.base_url}/logs", headers=self._get_headers(token)))

    def get_data_types(self, token: str):
        return self._handle_response(self.session.get(f"{self.base_url}/data_types", headers=self._get_headers(token)))

    def get_history(self, token: str, impersonate: str = None, data_type: str = None):
        url = f"{self.base_url}/history"
        params = []
        if impersonate:
            params.append(f"impersonate={impersonate}")
        if data_type:
            params.append(f"data_type={data_type}")
        if params:
            url += "?" + "&".join(params)
        return self._handle_response(self.session.get(url, headers=self._get_headers(token)))

    def get_data(self, token: str, val: str, impersonate: str = None):
        url = f"{self.base_url}/data/{val}"
        if impersonate:
            url += f"?impersonate={impersonate}"
        return self._handle_response(self.session.get(url, headers=self._get_headers(token)))

    def download_file(self, token: str, filename: str, impersonate: str = None):
        url = f"{self.base_url}/download/{filename}"
        if impersonate:
            url += f"?impersonate={impersonate}"
        response = self._handle_response(self.session.get(url, headers=self._get_headers(token)))
        if response.status_code == 200:
            encoded = base64.b64encode(response.content).decode()
            
            # Extract filename from Content-Disposition header
            out_filename = filename
            content_disposition = response.headers.get("content-disposition", "")
            if 'filename="' in content_disposition:
                out_filename = content_disposition.split('filename="')[1].split('"')[0]
            elif 'filename=' in content_disposition:
                out_filename = content_disposition.split('filename=')[1]
                
            return dict(content=encoded, filename=out_filename, base64=True)
        return None

    def upload_file(self, token: str, files: dict, client_id: str = None, data_type: str = "Ccf Data"):
        data = {"client_id": client_id} if client_id else {}
        data["data_type"] = data_type
        return self._handle_response(self.session.post(f"{self.base_url}/upload", headers=self._get_headers(token), files=files, data=data))

    def get_settings(self, token: str):
        return self._handle_response(self.session.get(f"{self.base_url}/settings", headers=self._get_headers(token)))

    def update_settings(self, token: str, settings: dict):
        return self._handle_response(self.session.post(f"{self.base_url}/settings", headers=self._get_headers(token), json=settings))

api_client = ApiClient(API_BASE_URL)

from datetime import datetime
from dash import html

def get_history_options(token, user_role=None, permissions=None, impersonate=None, data_type=None):
    if permissions is None: permissions = []
    try:
        response = api_client.get_history(token, impersonate, data_type)
        if response.status_code == 200:
            file_times = response.json()
        else:
            return []
    except Exception:
        return []
    now = datetime.now()
    today = now.date()
    options = []
    current_group = None
    for item in file_times:
        mtime = datetime.fromisoformat(item['time'])
        date = mtime.date()
        age_days = (today - date).days
        if age_days == 0:
            group_name = 'Today'
        elif age_days == 1:
            group_name = 'Yesterday'
        elif age_days <= 30:
            group_name = mtime.strftime('%b %d')
        elif age_days <= 90:
            group_name = mtime.strftime('%B')
        else:
            group_name = 'Earlier'
        if group_name != current_group:
            options.append({
                'label': html.Div(group_name, className='section-title mt-3 mb-1'),
                'value': f'HEADER_{group_name}',
                'disabled': True
            })
            current_group = group_name
        label = html.Span(item['name'], className='text-truncate ms-2')
        options.append({'label': label, 'value': item['name']})
    return options

def upload_file_to_api(contents, filename, token, client_id=None, data_type="Ccf Data"):
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        files = {'file': (filename, decoded)}
        response = api_client.upload_file(token, files, client_id=client_id, data_type=data_type)
        if response.status_code == 200:
            return response.json()
        else:
            print(f'Upload error: {response.text}')
            return None
    except Exception as e:
        print(f'Exception during upload: {e}')
        return None

@lru_cache(maxsize=16)
def get_dataframe(token: str, filename: str, impersonate: str = None) -> pd.DataFrame:
    """Fetches data from backend and caches it in Dash server memory as a DataFrame."""
    try:
        response = api_client.get_data(token, filename, impersonate)
        if response.status_code == 200:
            return pd.DataFrame(response.json())
        return pd.DataFrame()
    except Exception as e:
        print(f'Exception fetching dataframe for {filename}: {e}')
        return pd.DataFrame()
