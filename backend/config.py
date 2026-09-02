from sqlalchemy.orm import Session
from backend.database.models import Setting

def get_active_folders(db: Session) -> list:
    """
    Fetches the dynamic list of enabled folders from the database settings.
    """
    setting = db.query(Setting).filter(Setting.key == "active_folders").first()
    if setting and isinstance(setting.value, list):
        return setting.value
    # Default fallback to preserve existing behavior if setting isn't configured yet
    return ["ccf_data", "unimate_data", "cdr_data", "apr_data"]
