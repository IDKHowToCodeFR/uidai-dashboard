import requests
import base64
from functools import lru_cache
import pandas as pd
import os
from flask import request, has_request_context

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api")

_session = requests.Session()

def _get_headers(token: str = None):
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

def api_get(endpoint: str, token: str = None, **kwargs):
    """Generic wrapper for GET requests to the API."""
    url = f"{API_BASE_URL}/{endpoint.lstrip('/')}"
    return _session.get(url, headers=_get_headers(token), **kwargs)

def api_post(endpoint: str, token: str = None, **kwargs):
    """Generic wrapper for POST requests to the API."""
    url = f"{API_BASE_URL}/{endpoint.lstrip('/')}"
    return _session.post(url, headers=_get_headers(token), **kwargs)

def download_file(token: str, filename: str, impersonate: str = None):
    """Downloads and decodes a file from the API."""
    params = {}
    if impersonate:
        params["impersonate"] = impersonate
        
    response = api_get(f"download/{filename}", token=token, params=params)
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

from datetime import datetime
from dash import html

def get_history_options(token, user_role=None, permissions=None, impersonate=None, data_type=None):
    if permissions is None: permissions = []
    try:
        response = api_get("history", token=token, params={"impersonate": impersonate, "data_type": data_type})
        if response.status_code == 200:
            file_times = response.json()
        elif response.status_code == 401:
            return "UNAUTHORIZED"
        else:
            return []
    except Exception:
        return []
    now = datetime.now()
    today = now.date()
    options = []
    current_group = None
    for item in file_times:
        time_val = item.get('time')
        if not time_val:
            continue
        
        if isinstance(time_val, (int, float)):
            mtime = datetime.fromtimestamp(time_val)
        else:
            time_str = str(time_val)
            if time_str.endswith('Z'):
                time_str = time_str[:-1] + '+00:00'
            try:
                mtime = datetime.fromisoformat(time_str)
            except ValueError:
                # Fallback to current time so the file still appears in the list
                mtime = datetime.now()
                
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

def upload_file_to_api(contents, filename, token, client_id=None, data_type="CCF Data"):
    import base64
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        files = {'file': (filename, decoded)}
        response = api_post("upload", token=token, files=files, data={"client_id": client_id, "data_type": data_type})
        if response.status_code == 200:
            return response.json()
        else:
            print(f'Upload error: {response.text}')
            return None
    except Exception as e:
        print(f'Exception during upload: {e}')
        return None

def get_all_companies(token: str = None):
    try:
        response = api_get("companies", token=token)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching companies: {e}")
    return ["Digitech", "NSB"]

@lru_cache(maxsize=32)
def get_dataframe(token: str, filename: str, impersonate: str = None, 
                  companies: tuple = None, languages: tuple = None, 
                  start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """Fetches data from backend and caches it in Dash server memory as a DataFrame."""
    try:
        params = {"impersonate": impersonate}
        if companies:
            params["companies"] = ",".join(companies)
        if languages:
            params["languages"] = ",".join(languages)
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
            
        response = api_get(f"data/{filename}", token=token, params=params)
        if response.status_code == 200:
            return pd.DataFrame(response.json())
        return pd.DataFrame()
    except Exception as e:
        print(f'Exception fetching dataframe for {filename}: {e}')
        return pd.DataFrame()
