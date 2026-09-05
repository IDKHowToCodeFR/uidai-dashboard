from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.database.database import get_db
from backend.auth.auth_utils import get_current_user, require_permission
from backend.audit.audit_logger import add_log, load_logs, extract_request_metadata
from backend.settings.settings_manager import load_settings, save_settings

router = APIRouter()

@router.get('/settings')
async def get_settings(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return load_settings(db)

@router.post('/settings')
async def update_settings(request: Request, settings: dict, current_user: dict = Depends(require_permission('can_view_global')), db: Session = Depends(get_db)):
    save_settings(db, settings)
    meta = extract_request_metadata(request)
    add_log(db, 'SETTINGS_UPDATED', current_user['username'], 'Updated SLA targets', **meta)
    return {'message': 'Settings updated successfully'}

@router.get("/logs")
async def get_system_logs(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    logs = load_logs(db)
    logs.sort(key=lambda x: x['timestamp'] or "", reverse=True)
    return logs
