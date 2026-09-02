import pandas as pd
from backend.database.models import CCFData
from backend.data_ingestion.base_parser import parse_generic

"""
Pure domain module for parsing CCF Excel/CSV data.
Calculates derived Service Level (SL) and Average Handle Time (AHT) metrics.
"""

MAPPING = {
    'Company': 'company', 'Language': 'language', 'Date': 'date_logged', 'Call Timestamp': 'call_timestamp',
    'Day': 'day', 'Call Offered': 'call_offered', 'ABAN Calls in 10 Sec': 'aban_calls_10_sec', 'ACD Calls in 10 Sec': 'acd_calls_10_sec',
    'ACD Calls in 20 Sec': 'acd_calls_20_sec', 'ABAN Calls': 'aban_calls', 'Held Calls': 'held_calls',
    'ACD Calls': 'acd_calls', 'Hold Time': 'hold_time', 'ACD Time': 'acd_time', 'ACW Time': 'acw_time'
}
MODEL = CCFData
INDEX_ELEMENTS = ['company', 'language', 'call_timestamp']

async def parse_ccf(save_path: str, progress_callback=None) -> pd.DataFrame:
    return await parse_generic(
        save_path=save_path,
        progress_callback=progress_callback,
        dedupe_cols=['Company', 'Language', 'Call Timestamp'],
        inject_sheet_company=True
    )
