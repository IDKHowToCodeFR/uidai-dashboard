import pandas as pd
import numpy as np

"""
Pure domain module for parsing CCF Excel/CSV data.
Calculates derived Service Level (SL) and Average Handle Time (AHT) metrics.
"""
from backend.database.models import CCFData

MAPPING = {
    'Company': 'company', 'Language': 'language', 'Date': 'date_logged', 'Call Timestamp': 'call_timestamp',
    'Day': 'day', 'Call Offered': 'call_offered', 'ABAN Calls in 10 Sec': 'aban_calls_10_sec', 'ACD Calls in 10 Sec': 'acd_calls_10_sec',
    'ACD Calls in 20 Sec': 'acd_calls_20_sec', 'ABAN Calls': 'aban_calls', 'Held Calls': 'held_calls',
    'ACD Calls': 'acd_calls', 'Hold Time': 'hold_time', 'ACD Time': 'acd_time', 'ACW Time': 'acw_time'
}
MODEL = CCFData
INDEX_ELEMENTS = ['company', 'language', 'call_timestamp']

async def parse_ccf(save_path: str, progress_callback=None) -> pd.DataFrame:
    if progress_callback:
        await progress_callback(10, 'Parsing file...')
        
    if save_path.endswith('.csv'):
        df = pd.read_csv(save_path)
        df.columns = df.columns.str.strip()
    elif save_path.endswith('.xls') or save_path.endswith('.xlsx'):
        excel_file = pd.ExcelFile(save_path)
        dfs = []
        for i, sheet_name in enumerate(excel_file.sheet_names):
            if progress_callback:
                await progress_callback(10 + int(40 * (i / len(excel_file.sheet_names))), f'Parsing sheet {sheet_name}...')
            sheet_df = pd.read_excel(excel_file, sheet_name=sheet_name)
            sheet_df.columns = sheet_df.columns.str.strip()
            if 'Company' not in sheet_df.columns:
                sheet_df['Company'] = sheet_name
            dfs.append(sheet_df)
        df = pd.concat(dfs, ignore_index=True)
        
    if 'Company' in df.columns and 'Language' in df.columns and 'Call Timestamp' in df.columns:
        df.drop_duplicates(subset=['Company', 'Language', 'Call Timestamp'], keep='last', inplace=True)
            
    if progress_callback:
        await progress_callback(60, 'Cleaning data...')
        
    df.dropna(how='all', inplace=True)
    df.dropna(axis=1, how='all', inplace=True)

    numeric_cols = df.select_dtypes(include='number').columns
    df[numeric_cols] = df[numeric_cols].fillna(0)
    
    if progress_callback:
        await progress_callback(75, 'Formatting columns...')
        
    object_cols = df.select_dtypes(include=['object', 'string']).columns
    df[object_cols] = df[object_cols].fillna('Unknown')
    for col in object_cols:
        df[col] = df[col].astype(str).str.strip()
        


    return df
