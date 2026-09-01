import os
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from backend.database.models import FileMetadata, CCFData, UniMateData, CDRData
from backend.audit.audit_logger import add_log

def save_data(db: Session, df: pd.DataFrame, save_path: str, out_filename: str, username: str, data_type: str, mapping: dict, model, index_elements: list, meta: dict = None):
    file_meta = db.query(FileMetadata).filter_by(
        filename=out_filename,
        upload_directory=os.path.basename(os.path.dirname(save_path))
    ).first()
    
    if not file_meta:
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
    
    if data_type == "APR Data":
        aggregate_agent_metadata(db)

def aggregate_agent_metadata(db: Session):
    from backend.database.models import APRData, AgentMetadata
    import numpy as np
    
    df = pd.read_sql(
        db.query(APRData.login_id, APRData.agent_name, APRData.company, APRData.language, 
                 APRData.acd_calls, APRData.acd_time, APRData.acw_time, APRData.staffed_time, APRData.occupancy_with_acw).statement,
        db.bind
    )
    if df.empty:
        return
        
    def hhmmss_to_seconds(time_str):
        if pd.isna(time_str) or not isinstance(time_str, str):
            return 0
        try:
            parts = str(time_str).split(':')
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            return 0
        except:
            return 0
            
    df['acd_time_sec'] = df['acd_time'].apply(hhmmss_to_seconds)
    df['acw_time_sec'] = df['acw_time'].apply(hhmmss_to_seconds)
    df['staffed_time_sec'] = df['staffed_time'].apply(hhmmss_to_seconds)
    
    grp = df.groupby(['login_id']).agg({
        'agent_name': 'last',
        'company': 'last',
        'language': 'last',
        'acd_calls': 'sum',
        'acd_time_sec': 'sum',
        'acw_time_sec': 'sum',
        'staffed_time_sec': 'sum',
        'occupancy_with_acw': 'mean'
    }).reset_index()
    
    grp['Calls Per Hour'] = np.where(grp['staffed_time_sec'] > 0, grp['acd_calls'] / (grp['staffed_time_sec'] / 3600), 0)
    grp['AHT (sec)'] = np.where(grp['acd_calls'] > 0, (grp['acd_time_sec'] + grp['acw_time_sec']) / grp['acd_calls'], 0)
    
    grp['composite_score'] = (
        (grp['Calls Per Hour'] / 15.0) * 40 + 
        (grp['occupancy_with_acw'] / 100.0) * 30 + 
        (np.where(grp['AHT (sec)'] > 0, 240.0 / grp['AHT (sec)'], 0)) * 30
    ).round(2)
    
    import re
    def clean_name(name):
        if not isinstance(name, str): return ""
        name = re.sub(r'^(digitech|nsb)_', '', name, flags=re.IGNORECASE)
        return name.replace('_', ' ').strip()
        
    records = []
    for _, row in grp.iterrows():
        records.append({
            'anslogin': str(row['login_id']),
            'name': clean_name(row['agent_name']),
            'company': str(row['company']),
            'language': str(row['language']),
            'total_acd_calls': int(row['acd_calls']),
            'total_staffed_time_sec': int(row['staffed_time_sec']),
            'total_acd_time_sec': int(row['acd_time_sec']),
            'total_acw_time_sec': int(row['acw_time_sec']),
            'avg_occupancy': float(row['occupancy_with_acw']),
            'composite_score': float(row['composite_score'])
        })
        
    batch_size = 1000
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        stmt = sqlite_insert(AgentMetadata).values(batch)
        update_dict = {c.name: c for c in stmt.excluded if c.name not in ('id', 'anslogin')}
        stmt = stmt.on_conflict_do_update(
            index_elements=['anslogin'],
            set_=update_dict
        )
        db.execute(stmt)
    db.commit()
