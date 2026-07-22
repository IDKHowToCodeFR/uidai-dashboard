import os
import pandas as pd
import numpy as np

RAW_DIR = "data/unprocessed"
PROCESSED_DIR = "data/processed"

def process_data():
    if not os.path.exists(PROCESSED_DIR):
        os.makedirs(PROCESSED_DIR)

    files = [f for f in os.listdir(RAW_DIR) if f.endswith(('.xlsx', '.xls'))]
    
    if not files:
        print(f"No Excel files found in {RAW_DIR}")
        return

    for file in files:
        print(f"Processing {file}...")
        file_path = os.path.join(RAW_DIR, file)
        try:
            # Read excel
            df = pd.read_excel(file_path, engine='openpyxl')
            
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

            # Save to processed as XLSX
            out_filename = os.path.splitext(file)[0] + "_processed.xlsx"
            out_path = os.path.join(PROCESSED_DIR, out_filename)
            df.to_excel(out_path, index=False, engine='openpyxl')
            print(f"Saved processed data to {out_path}")
            
        except Exception as e:
            print(f"Error processing {file}: {e}")

if __name__ == "__main__":
    process_data()
