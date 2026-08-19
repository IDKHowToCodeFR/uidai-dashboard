import pandas as pd
import numpy as np

class CCFParser:
    """
    Pure domain module for parsing CCF Excel/CSV data.
    Calculates derived Service Level (SL) and Average Handle Time (AHT) metrics.
    """
    @staticmethod
    async def parse(save_path: str, progress_callback=None) -> pd.DataFrame:
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
            
        # Derived Quantities
        if 'ACD Calls in 20 Sec' in df.columns and 'Call Offered' in df.columns and 'ABAN Calls in 10 Sec' in df.columns:
            denom = (df['Call Offered'] - df['ABAN Calls in 10 Sec'])
            df['Service Level %'] = pd.Series(np.where(denom > 0, (df['ACD Calls in 20 Sec'] / denom) * 100, 0), index=df.index)
            df['Service Level Status'] = np.where(df['Service Level %'] > 85, 'Good', 'Penalty')
            
        if 'Hold Time' in df.columns and 'ACD Calls' in df.columns:
            df['Avg Hold Time'] = pd.Series(np.where(df['ACD Calls'] > 0, df['Hold Time'] / df['ACD Calls'], 0), index=df.index)
            df['Hold Time Status'] = np.where(df['Avg Hold Time'] <= 20, 'Good', 'Penalty')
            
        if 'ACD Time' in df.columns and 'ACW Time' in df.columns and 'Hold Time' in df.columns and 'ACD Calls' in df.columns:
            df['Avg Handle Time'] = pd.Series(np.where(df['ACD Calls'] > 0, (df['ACD Time'] + df['ACW Time'] + df['Hold Time']) / df['ACD Calls'], 0), index=df.index)
            df['AHT Status'] = np.where(df['Avg Handle Time'] <= 240, 'Good', 'Penalty')

        return df
