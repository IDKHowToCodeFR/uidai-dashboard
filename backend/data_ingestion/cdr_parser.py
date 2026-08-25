import pandas as pd
import numpy as np

"""
Pure domain module for parsing CDR Excel/CSV data.
"""
async def parse_cdr(save_path: str, progress_callback=None) -> pd.DataFrame:
    if progress_callback:
        await progress_callback(10, 'Parsing file...')
        
    if save_path.endswith('.csv'):
        df = pd.read_csv(save_path)
        df.columns = df.columns.str.strip()
    elif save_path.endswith('.xls') or save_path.endswith('.xlsx'):
        excel_file = pd.ExcelFile(save_path, engine='openpyxl')
        dfs = []
        for i, sheet_name in enumerate(excel_file.sheet_names):
            if progress_callback:
                await progress_callback(10 + int(40 * (i / len(excel_file.sheet_names))), f'Parsing sheet {sheet_name}...')
            sheet_df = pd.read_excel(excel_file, sheet_name=sheet_name)
            sheet_df.columns = sheet_df.columns.str.strip()
            dfs.append(sheet_df)
        df = pd.concat(dfs, ignore_index=True)
        if 'Call Id' in df.columns:
            df.drop_duplicates(subset=['Call Id'], keep='last', inplace=True)
            
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
        
    # Parse Vendor and Language from split1
    if 'split1' in df.columns:
        # split1 is numeric (e.g. 811, 922) — convert to string for parsing
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
                '11': 'Hindi',
                '12': 'English',
                '13': 'Bengali',
                '14': 'Telugu',
                '15': 'Marathi',
                '16': 'Tamil',
                '17': 'Gujarati',
                '18': 'Kannada',
                '19': 'Odia',
                '20': 'Malayalam',
                '21': 'Punjabi',
                '22': 'Assamese',
            }
            return LANG_CODE_MAP.get(lang_code, f"Lang_{lang_code}")
            
        df['Company'] = df['split1'].apply(extract_vendor)
        df['Language'] = df['split1'].apply(extract_language)

    return df
