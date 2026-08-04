from fastapi import APIRouter, Depends, HTTPException
from backend.api.auth_utils import (
    get_current_user, PermissionChecker, add_log,
    load_settings, save_settings, load_logs
)

router = APIRouter()

@router.get('/settings')
async def get_settings(current_user: dict = Depends(get_current_user)):
    return load_settings()

@router.post('/settings')
async def update_settings(settings: dict, current_user: dict = Depends(PermissionChecker('can_view_global'))):
    save_settings(settings)
    add_log('SETTINGS_UPDATED', current_user['username'], 'Updated SLA targets')
    return {'message': 'Settings updated successfully'}

@router.get("/logs")
async def get_system_logs(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin only")
    logs = load_logs()
    logs.sort(key=lambda x: x['timestamp'], reverse=True)
    return logs
