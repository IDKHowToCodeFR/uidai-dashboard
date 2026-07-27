import os
import pandas as pd
import numpy as np

RAW_DIR = "data/unprocessed"
PROCESSED_DIR = "data/processed"

def process_data():
    if not os.path.exists(PROCESSED_DIR):
        os.makedirs(PROCESSED_DIR)

    files = [f for f in os.listdir(RAW_DIR) if f.endswith(('.xlsx', '.xls', '.csv'))]
    
    if not files:
        print(f"No files found in {RAW_DIR}")
        return

    for file in files:
        out_filename = os.path.splitext(file)[0] + "_processed.csv"
        out_path = os.path.join(PROCESSED_DIR, out_filename)
        
        # Check if already processed
        if os.path.exists(out_path):
            print(f"Skipping {file}, {out_filename} already exists.")
            continue
            
        print(f"Processing {file}...")
        file_path = os.path.join(RAW_DIR, file)
        try:
            # Read excel or csv
            if file.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                excel_file = pd.ExcelFile(file_path, engine='openpyxl')
                dfs = []
                for sheet_name in excel_file.sheet_names:
                    sheet_df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    # Infer company from sheet name if not exists
                    if 'Company' not in sheet_df.columns:
                        sheet_df['Company'] = sheet_name
                    dfs.append(sheet_df)
                df = pd.concat(dfs, ignore_index=True)
            
            # Common cleaning steps
            # 1. Fill NaNs in numeric columns with 0
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            df[numeric_cols] = df[numeric_cols].fillna(0)
            
            # 2. Fill NaNs in object columns with 'Unknown'
            object_cols = df.select_dtypes(include=['object', 'string']).columns
            df[object_cols] = df[object_cols].fillna('Unknown')
            
            # 3. Strip whitespace from string columns
            for col in object_cols:
                df[col] = df[col].astype(str).str.strip()
                
            # 4. Drop fully empty rows/cols
            df.dropna(how='all', inplace=True)
            df.dropna(axis=1, how='all', inplace=True)
            
            # 5. Derived Quantities
            if 'ACD Calls in 20 Sec' in df.columns and 'Call Offered' in df.columns and 'ABAN Calls in 10 Sec' in df.columns:
                denom = (df['Call Offered'] - df['ABAN Calls in 10 Sec'])
                df['Service Level %'] = np.where(denom > 0, (df['ACD Calls in 20 Sec'] / denom) * 100, 0)
                df['Service Level Status'] = np.where(df['Service Level %'] > 85, 'Good', 'Penalty')
                
            if 'Hold Time' in df.columns and 'ACD Calls' in df.columns:
                df['Avg Hold Time'] = np.where(df['ACD Calls'] > 0, df['Hold Time'] / df['ACD Calls'], 0)
                df['Hold Time Status'] = np.where(df['Avg Hold Time'] <= 20, 'Good', 'Penalty')
                
            if 'ACD Time' in df.columns and 'ACW Time' in df.columns and 'Hold Time' in df.columns and 'ACD Calls' in df.columns:
                df['Avg Handle Time'] = np.where(df['ACD Calls'] > 0, (df['ACD Time'] + df['ACW Time'] + df['Hold Time']) / df['ACD Calls'], 0)
                df['AHT Status'] = np.where(df['Avg Handle Time'] <= 240, 'Good', 'Penalty')

            # Save to processed as CSV
            df.to_csv(out_path, index=False)
            print(f"Saved processed data to {out_path}")
            
        except Exception as e:
            print(f"Error processing {file}: {e}")

if __name__ == "__main__":
    process_data()
