import pandas as pd
import numpy as np

async def parse_generic(
    save_path: str,
    progress_callback=None,
    custom_transform=None,
    dedupe_cols=None,
    inject_sheet_company=False
) -> pd.DataFrame:
    """
    Unified generic parser to load, clean, and format Excel/CSV data.
    """
    if progress_callback:
        await progress_callback(10, 'Parsing file...')
        
    if save_path.endswith('.csv'):
        df = pd.read_csv(save_path)
        df.columns = df.columns.str.strip()
    else:
        excel_file = pd.ExcelFile(save_path)
        dfs = []
        for i, sheet_name in enumerate(excel_file.sheet_names):
            if progress_callback:
                await progress_callback(10 + int(40 * (i / len(excel_file.sheet_names))), f'Parsing sheet {sheet_name}...')
            sheet_df = pd.read_excel(excel_file, sheet_name=sheet_name)
            sheet_df.columns = sheet_df.columns.str.strip()
            
            if inject_sheet_company and 'Company' not in sheet_df.columns:
                sheet_df['Company'] = sheet_name
                
            dfs.append(sheet_df)
        df = pd.concat(dfs, ignore_index=True)
            
    if progress_callback:
        await progress_callback(50, 'Cleaning data...')
        
    df.dropna(how='all', inplace=True)
    df.dropna(axis=1, how='all', inplace=True)
    
    # Run dataset-specific transformations
    if custom_transform:
        df = custom_transform(df)
        
    # Drop duplicates if specified
    if dedupe_cols:
        missing_cols = [c for c in dedupe_cols if c not in df.columns]
        if not missing_cols:
            df.drop_duplicates(subset=dedupe_cols, keep='last', inplace=True)

    if progress_callback:
        await progress_callback(80, 'Formatting columns...')

    numeric_cols = df.select_dtypes(include='number').columns
    df[numeric_cols] = df[numeric_cols].fillna(0)
    
    object_cols = df.select_dtypes(include=['object', 'string']).columns
    df[object_cols] = df[object_cols].fillna('Unknown')
    for col in object_cols:
        df[col] = df[col].astype(str).str.strip()
        
    return df
