import pandas as pd
from backend.database.models import CDRData
from backend.data_ingestion.base_parser import parse_generic

"""
Pure domain module for parsing CDR Excel/CSV data.
"""

MAPPING = {
    'Call Id': 'call_id', 'acwtime': 'acwtime', 'ansholdtime': 'ansholdtime', 'duration': 'duration',
    'segstart': 'segstart', 'segstartutc': 'segstartutc', 'segstop': 'segstop', 'segstoputc': 'segstoputc',
    'talktime': 'talktime', 'split1': 'split1', 'transferred': 'transferred', 'agt_released': 'agt_released',
    'origlogin': 'origlogin', 'anslogin': 'anslogin', 'Company': 'company', 'Language': 'language'
}
MODEL = CDRData
INDEX_ELEMENTS = ['call_id']

def transform_cdr(df: pd.DataFrame) -> pd.DataFrame:
    if 'split1' in df.columns:
        df['split1'] = df['split1'].astype(str).str.strip()
        
        def extract_vendor(split_val):
            if not split_val or split_val == 'nan' or len(split_val) == 0:
                return 'Unknown'
            first_digit = split_val[0]
            if first_digit == '8':
                return 'Digitech'
            elif first_digit == '9':
                return 'NSB'
            return 'Unknown'
            
        def extract_language(split_val):
            if not split_val or split_val == 'nan' or len(split_val) < 3:
                return 'Unknown'
            lang_code = split_val[1:3]
            LANG_CODE_MAP = {
                '11': 'Hindi', '12': 'English', '13': 'Bengali', '14': 'Telugu',
                '15': 'Marathi', '16': 'Tamil', '17': 'Gujarati', '18': 'Kannada',
                '19': 'Odia', '20': 'Malayalam', '21': 'Punjabi', '22': 'Assamese',
            }
            return LANG_CODE_MAP.get(lang_code, f"Lang_{lang_code}")
            
        df['Company'] = df['split1'].apply(extract_vendor)
        df['Language'] = df['split1'].apply(extract_language)
        
    # Date parsing as per format.txt: DD-MM-YYYY HH:MM:SS
    if 'segstart' in df.columns:
        df['segstart'] = pd.to_datetime(df['segstart'], format='%d-%m-%Y %H:%M:%S', errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
    if 'segstop' in df.columns:
        df['segstop'] = pd.to_datetime(df['segstop'], format='%d-%m-%Y %H:%M:%S', errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')

    return df

async def parse_cdr(save_path: str, progress_callback=None) -> pd.DataFrame:
    return await parse_generic(
        save_path=save_path,
        progress_callback=progress_callback,
        custom_transform=transform_cdr,
        dedupe_cols=['Call Id']
    )
