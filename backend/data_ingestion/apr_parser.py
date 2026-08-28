import pandas as pd
import numpy as np

"""
Pure domain module for parsing APR Excel/CSV data.
"""
from backend.database.models import APRData

MAPPING = {
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
MODEL = APRData
INDEX_ELEMENTS = ['date_logged', 'login_id']

async def parse_apr(save_path: str, progress_callback=None) -> pd.DataFrame:
    if progress_callback:
        await progress_callback(10, 'Parsing file...')
        
    if save_path.endswith('.csv'):
        df = pd.read_csv(save_path)
    else:
        df = pd.read_excel(save_path)
        
    df.columns = df.columns.str.strip()
    
    if progress_callback:
        await progress_callback(50, 'Cleaning data...')
        
    df.dropna(how='all', inplace=True)
    df.dropna(axis=1, how='all', inplace=True)
    
    # Determine company based on Login ID
    if 'Login ID' in df.columns:
        df['Login ID'] = df['Login ID'].astype(str).str.strip()
        df['Company'] = np.where(df['Login ID'].str.startswith('56'), 'Digitech',
                           np.where(df['Login ID'].str.startswith('57'), 'NSB', 'Unknown'))
    else:
        df['Company'] = 'Unknown'
        
    if progress_callback:
        await progress_callback(80, 'Formatting columns...')

    if 'Split / Skill' in df.columns:
        df['Language'] = df['Split / Skill'].astype(str).str.split('_').str[-1].str.strip()
    else:
        df['Language'] = 'Unknown'

    numeric_cols = df.select_dtypes(include='number').columns
    df[numeric_cols] = df[numeric_cols].fillna(0)
    
    object_cols = df.select_dtypes(include=['object', 'string']).columns
    df[object_cols] = df[object_cols].fillna('Unknown')
    for col in object_cols:
        df[col] = df[col].astype(str).str.strip()
        
    return df
