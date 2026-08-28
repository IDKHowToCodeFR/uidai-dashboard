import os
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from backend.database.models import FileMetadata, CCFData, UniMateData, CDRData
from backend.audit.audit_logger import add_log

def save_data(db: Session, df: pd.DataFrame, save_path: str, out_filename: str, username: str, data_type: str, mapping: dict, model, index_elements: list, meta: dict = None):
    file_meta = FileMetadata(
        filename=out_filename,
        upload_directory=os.path.basename(os.path.dirname(save_path)),
        data_type=data_type,
        uploader=username,
        size_bytes=os.path.getsize(save_path)
    )
    db.add(file_meta)
    db.commit()
    db.refresh(file_meta)
        
    df = df.rename(columns=mapping)
    available_cols = [col for col in mapping.values() if col in df.columns]
    records = df[available_cols].to_dict('records')
        
    for record in records:
        record['file_id'] = file_meta.id
            
    batch_size = 1000
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        stmt = sqlite_insert(model).values(batch)
        update_dict = {c.name: c for c in stmt.excluded if c.name not in ('id',)}
        stmt = stmt.on_conflict_do_update(
            index_elements=index_elements,
            set_=update_dict
        )
        db.execute(stmt)
        
    if meta is None: meta = {}
    add_log(db, 'FILE_UPLOADED', username, f'Uploaded and ingested {data_type} file: {out_filename}', **meta)
    db.commit()
