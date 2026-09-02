import pandas as pd
import numpy as np
from backend.database.models import APRData
from backend.data_ingestion.base_parser import parse_generic

"""
Pure domain module for parsing APR Excel/CSV data.
"""

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

def transform_apr(df: pd.DataFrame) -> pd.DataFrame:
    if 'Login ID' in df.columns:
        df['Login ID'] = df['Login ID'].astype(str).str.strip()
        df['Company'] = np.where(df['Login ID'].str.startswith('56'), 'Digitech',
                           np.where(df['Login ID'].str.startswith('57'), 'NSB', 'Unknown'))
    else:
        df['Company'] = 'Unknown'
        
    if 'Split / Skill' in df.columns:
        df['Language'] = df['Split / Skill'].astype(str).str.split('_').str[-1].str.strip()
    else:
        df['Language'] = 'Unknown'
        
    return df

async def parse_apr(save_path: str, progress_callback=None) -> pd.DataFrame:
    return await parse_generic(
        save_path=save_path,
        progress_callback=progress_callback,
        custom_transform=transform_apr
    )
