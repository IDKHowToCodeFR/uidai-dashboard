import pandas as pd
import numpy as np

"""
Pure domain module for parsing UniMate Excel/CSV data.
"""
async def parse_unimate(save_path: str, progress_callback=None) -> pd.DataFrame:
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
    
    # Determine company based on DNIS
    if 'DNIS' in df.columns:
        df['DNIS'] = df['DNIS'].astype(str).str.strip()
        df['Company'] = np.where(df['DNIS'].str.startswith('56'), 'Digitech',
                           np.where(df['DNIS'].str.startswith('57'), 'NSB', 'Unknown'))
    else:
        df['Company'] = 'Unknown'
        
    if 'UCID' in df.columns:
        df.drop_duplicates(subset=['UCID'], keep='last', inplace=True)
        
    if progress_callback:
        await progress_callback(80, 'Formatting columns...')
        
    if 'Day of Week' in df.columns:
        day_map = {1: 'Sunday', 2: 'Monday', 3: 'Tuesday', 4: 'Wednesday', 5: 'Thursday', 6: 'Friday', 7: 'Saturday'}
        df['Day of Week'] = pd.to_numeric(df['Day of Week'], errors='coerce').map(day_map).fillna(df['Day of Week'])

    if 'Language' in df.columns:
        lang_map = {
            'gu-in': 'Gujarati', 'te-in': 'Telugu', 'mr-in': 'Marathi', 
            'en-in': 'English', 'ml-in': 'Malayalam', 'hi-in': 'Hindi', 
            'pa-in': 'Punjabi', 'bn-in': 'Bengali', 'or-in': 'Odia', 
            'kn-in': 'Kannada', 'ta-in': 'Tamil'
        }
        df['Language'] = df['Language'].astype(str).str.strip().str.lower().map(lang_map).fillna(df['Language'])

    if 'Call Duration' in df.columns:
        def duration_to_seconds(x):
            try:
                if pd.isna(x): return 0
                parts = str(x).split(':')
                if len(parts) == 3:
                    # Handle datetime string format like '1899-12-31 00:07:23'
                    hours_str = parts[0].split(' ')[-1]
                    return int(hours_str) * 3600 + int(parts[1]) * 60 + int(float(parts[2]))
            except Exception:
                pass
            return 0
        df['Call Duration'] = df['Call Duration'].apply(duration_to_seconds)

    object_cols = df.select_dtypes(include=['object', 'string']).columns
    df[object_cols] = df[object_cols].fillna('Unknown')
    for col in object_cols:
        df[col] = df[col].astype(str).str.strip()
        
    return df
