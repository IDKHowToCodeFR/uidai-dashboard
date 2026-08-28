import os
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from backend.database.models import FileMetadata, CCFData, UniMateData, CDRData
from backend.auth.auth_utils import add_log

def _save_data(db: Session, df: pd.DataFrame, save_path: str, out_filename: str, username: str, data_type: str, mapping: dict, model, index_elements: list, meta: dict = None):
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

def save_ccf_data(db: Session, df: pd.DataFrame, save_path: str, out_filename: str, username: str, data_type: str, meta: dict = None):
    mapping = {
        'Company': 'company', 'Language': 'language', 'Date': 'date_logged', 'Call Timestamp': 'call_timestamp',
        'Day': 'day', 'Call Offered': 'call_offered', 'ABAN Calls in 10 Sec': 'aban_calls_10_sec', 'ACD Calls in 10 Sec': 'acd_calls_10_sec',
        'ACD Calls in 20 Sec': 'acd_calls_20_sec', 'ABAN Calls': 'aban_calls', 'Held Calls': 'held_calls',
        'Service Level %': 'service_level_pct', 'Service Level Status': 'service_level_status', 'ACD Calls': 'acd_calls',
        'Hold Time': 'hold_time', 'Avg Hold Time': 'avg_hold_time', 'Hold Time Status': 'hold_time_status',
        'ACD Time': 'acd_time', 'ACW Time': 'acw_time', 'Avg Handle Time': 'avg_handle_time', 'AHT Status': 'aht_status'
    }
    _save_data(db, df, save_path, out_filename, username, data_type, mapping, CCFData, ['company', 'language', 'call_timestamp'], meta)

def save_unimate_data(db: Session, df: pd.DataFrame, save_path: str, out_filename: str, username: str, data_type: str, meta: dict = None):
    mapping = {
        'UCID': 'ucid', 'Session ID': 'session_id', 'Company': 'company', 'Day of Week': 'day_of_week',
        'Call Start Time': 'call_start_time', 'Call End Time': 'call_end_time', 'Call Duration': 'call_duration',
        'ANI': 'ani', 'DNIS': 'dnis', 'Language': 'language', 'Authentication': 'authentication',
        'Authentication Mechanism': 'auth_mechanism', 'Termination Type': 'termination_type',
        'Termination Reason': 'termination_reason', 'Description': 'description', 'Region': 'region'
    }
    _save_data(db, df, save_path, out_filename, username, data_type, mapping, UniMateData, ['ucid'], meta)

def save_cdr_data(db: Session, df: pd.DataFrame, save_path: str, out_filename: str, username: str, data_type: str, meta: dict = None):
    mapping = {
        'Call Id': 'call_id', 'acwtime': 'acwtime', 'ansholdtime': 'ansholdtime', 'duration': 'duration',
        'segstart': 'segstart', 'segstartutc': 'segstartutc', 'segstop': 'segstop', 'segstoputc': 'segstoputc',
        'talktime': 'talktime', 'split1': 'split1', 'transferred': 'transferred', 'agt_released': 'agt_released',
        'origlogin': 'origlogin', 'anslogin': 'anslogin', 'Company': 'company', 'Language': 'language'
    }
    _save_data(db, df, save_path, out_filename, username, data_type, mapping, CDRData, ['call_id'], meta)


def save_apr_data(db: Session, df: pd.DataFrame, save_path: str, out_filename: str, username: str, data_type: str, meta: dict = None):
    from backend.database.models import APRData
    mapping = {
        'Date': 'date_logged', 'Agent Name': 'agent_name', 'Login ID': 'login_id', 
        'ACD Calls': 'acd_calls', 'Avg ACD Time': 'avg_acd_time', 'Avg ACW Time': 'avg_acw_time', 
        '% Agent Occupancy with ACW': 'occupancy_with_acw', '% Agent Occupancy without ACW': 'occupancy_without_acw',
        'ACD Time': 'acd_time', 'ACW Time': 'acw_time', 'Agent Ring Time': 'agent_ring_time',
        'Other Time': 'other_time', 'AUX Time': 'aux_time', 'Avail Time': 'avail_time',
        'Staffed Time': 'staffed_time', 'Held Calls': 'held_calls', 'Tea Break': 'tea_break',
        'Lunch / Dinner': 'lunch_dinner', 'Quality Feedback': 'quality_feedback', 'Email Support': 'email_support',
        'Briefing': 'briefing', 'System Down': 'system_down', 'Meeting': 'meeting',
        'Trans Out': 'trans_out', 'Split / Skill': 'split_skill', 'Conf': 'conf',
        'Company': 'company', 'Language': 'language'
    }
    _save_data(db, df, save_path, out_filename, username, data_type, mapping, APRData, ['date_logged', 'login_id'], meta)
