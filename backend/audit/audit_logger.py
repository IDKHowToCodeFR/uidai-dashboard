from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from backend.database.models import AuditLog

def load_logs(db: Session) -> List[dict]:
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).all()
    return [{
        "timestamp": l.timestamp, 
        "action": l.action, 
        "username": l.username, 
        "details": l.details, 
        "ip_address": l.ip_address,
        "user_agent": l.user_agent,
        "endpoint": l.endpoint
    } for l in logs]

def extract_request_metadata(request) -> dict:
    meta = {"ip_address": "Unknown", "user_agent": "Unknown", "endpoint": "Unknown"}
    if not request:
        return meta
    
    headers = request.headers if hasattr(request, "headers") else {}
    
    # Extract IP
    if "x-forwarded-for" in headers:
        ip = headers["x-forwarded-for"].split(",")[0].strip()
        if ip:
            meta["ip_address"] = ip
    elif "x-real-ip" in headers:
        ip = headers["x-real-ip"].strip()
        if ip:
            meta["ip_address"] = ip
    elif hasattr(request, "client") and request.client and request.client.host:
        meta["ip_address"] = request.client.host

    # Extract User Agent
    if "user-agent" in headers:
        meta["user_agent"] = headers["user-agent"]
        
    # Extract Endpoint
    if hasattr(request, "url"):
        meta["endpoint"] = str(request.url.path)
        
    return meta

def add_log(db: Session, action: str, username: str, details: str = "", ip_address: str = None, user_agent: str = None, endpoint: str = None):
    timestamp_iso = datetime.now().isoformat()
    log_entry = AuditLog(
        timestamp=timestamp_iso,
        action=action,
        username=username,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        endpoint=endpoint
    )
    db.add(log_entry)
    db.commit()
    

def archive_old_logs(db: Session, days=90):
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
    db.query(AuditLog).filter(AuditLog.timestamp < cutoff_date).delete()
    db.commit()
