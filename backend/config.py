from sqlalchemy.orm import Session
from backend.database.models import Setting

class ActiveFoldersConfig:
    """
    Configuration module for active ingestion folders.
    Fetches the dynamic list of enabled folders from the database settings.
    """
    @staticmethod
    def get_active_folders(db: Session) -> list:
        setting = db.query(Setting).filter(Setting.key == "active_folders").first()
        if setting and isinstance(setting.value, list):
            return setting.value
        # Default fallback to preserve existing behavior if setting isn't configured yet
        return ["ccf_data"]
