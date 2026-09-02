from sqlalchemy.orm import Session
from backend.database.models import Setting

DEFAULT_SETTINGS = {
    "radar_sla_targets": [85, 95, 95, 85, 85, 85]
}

def load_settings(db: Session) -> dict:
    settings = db.query(Setting).all()
    if not settings:
        return DEFAULT_SETTINGS.copy()
    return {s.key: s.value for s in settings}

def save_settings(db: Session, settings: dict):
    for k, v in settings.items():
        setting = db.query(Setting).filter(Setting.key == k).first()
        if setting:
            setting.value = v
        else:
            setting = Setting(key=k, value=v)
            db.add(setting)
    db.commit()
