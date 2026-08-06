import os
import json
from datetime import datetime
from backend.api.database import SessionLocal, engine, Base
from backend.api.models import User, UserPermission, AuditLog, Setting
import bcrypt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

def migrate_users(db):
    users_file = os.path.join(DATA_DIR, 'users.json')
    if os.path.exists(users_file):
        with open(users_file, 'r') as f:
            users_data = json.load(f)
        
        for username, data in users_data.items():
            existing = db.query(User).filter(User.username == username).first()
            if not existing:
                user = User(
                    username=username,
                    password_hash=data.get('password'),
                    company_name=data.get('user', username),
                    login_count=data.get('login_count', 0),
                    last_login=data.get('last_login')
                )
                db.add(user)
                db.flush() # get user.id
                
                permissions = data.get('permissions', [])
                for perm in permissions:
                    up = UserPermission(user_id=user.id, permission_name=perm)
                    db.add(up)
        print("Migrated users.json")

def migrate_logs(db):
    logs_file = os.path.join(DATA_DIR, 'logs.json')
    if os.path.exists(logs_file):
        with open(logs_file, 'r') as f:
            logs_data = json.load(f)
            
        for log in logs_data:
            audit = AuditLog(
                timestamp=log.get('timestamp', datetime.now().isoformat()),
                action=log.get('action', 'UNKNOWN'),
                username=log.get('username', 'system'),
                details=log.get('details', '')
            )
            db.add(audit)
        print("Migrated logs.json")

def migrate_settings(db):
    settings_file = os.path.join(DATA_DIR, 'settings.json')
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as f:
            settings_data = json.load(f)
            
        for key, value in settings_data.items():
            existing = db.query(Setting).filter(Setting.key == key).first()
            if not existing:
                setting = Setting(key=key, value=value)
                db.add(setting)
        print("Migrated settings.json")

def run_migration():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        migrate_users(db)
        migrate_logs(db)
        migrate_settings(db)
        db.commit()
        print("Migration complete!")
    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
