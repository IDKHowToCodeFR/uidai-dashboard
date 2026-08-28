import pandas as pd
import numpy as np
from backend.database.models import UniMateData
from backend.data_ingestion.base_parser import parse_generic

"""
Pure domain module for parsing UniMate Excel/CSV data.
"""

MAPPING = {
    'UCID': 'ucid', 'Session ID': 'session_id', 'Company': 'company', 'Day of Week': 'day_of_week',
    'Call Start Time': 'call_start_time', 'Call End Time': 'call_end_time', 'Call Duration': 'call_duration',
    'ANI': 'ani', 'DNIS': 'dnis', 'Language': 'language', 'Authentication': 'authentication',
    'Authentication Mechanism': 'auth_mechanism', 'Termination Type': 'termination_type',
    'Termination Reason': 'termination_reason', 'Description': 'description', 'Region': 'region'
}
MODEL = UniMateData
INDEX_ELEMENTS = ['ucid']

def transform_unimate(df: pd.DataFrame) -> pd.DataFrame:
    # Determine company based on DNIS
    if 'DNIS' in df.columns:
        df['DNIS'] = df['DNIS'].astype(str).str.strip()
        df['Company'] = np.where(df['DNIS'].str.startswith('56'), 'Digitech',
                           np.where(df['DNIS'].str.startswith('57'), 'NSB', 'Unknown'))
    else:
        df['Company'] = 'Unknown'
        
    if 'Day of Week' in df.columns:
        day_map = {1: 'Sunday', 2: 'Monday', 3: 'Tuesday', 4: 'Wednesday', 5: 'Thursday', 6: 'Friday', 7: 'Saturday'}
        df['Day of Week'] = pd.to_numeric(df['Day of Week'], errors='coerce').map(day_map).fillna(df['Day of Week'])

    if 'Language' in df.columns:
        lang_map = {
            'gu-in': 'Gujarati', 'te-in': 'Telugu', 'mr-in': 'Marathi', 
            'en-in': 'English', 'ml-in': 'Malayalam', 'hi-in': 'Hindi', 
            'pa-in': 'Punjabi', 'bn-in': 'Bengali', 'or-in': 'Odia', 
            'kn-in': 'Kannada', 'ta-in': 'Tamil', 'as-in': 'Assamese'
        }
        df['Language'] = df['Language'].astype(str).str.strip().str.lower().map(lang_map).fillna(df['Language'])

    if 'Call Duration' in df.columns:
        def duration_to_seconds(x):
            try:
                if pd.isna(x): return 0
                parts = str(x).split(':')
                if len(parts) == 3:
                    hours_str = parts[0].split(' ')[-1]
                    return int(hours_str) * 3600 + int(parts[1]) * 60 + int(float(parts[2]))
            except Exception:
                pass
            return 0
        df['Call Duration'] = df['Call Duration'].apply(duration_to_seconds)
        
    return df

async def parse_unimate(save_path: str, progress_callback=None) -> pd.DataFrame:
    return await parse_generic(
        save_path=save_path,
        progress_callback=progress_callback,
        custom_transform=transform_unimate,
        dedupe_cols=['UCID']
    )
