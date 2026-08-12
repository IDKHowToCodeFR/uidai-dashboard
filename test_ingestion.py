import asyncio
import os
import sys

# Add root directory to path to resolve backend imports
sys.path.insert(0, os.path.abspath("."))

from backend.data_ingestion.websockets import process_file_background

save_path = os.path.abspath(r"backend\data\unprocessed\uidai_july_trend_data.xlsx")
out_filename = "test_uidai_july_trend_data.xlsx"

async def main():
    if not os.path.exists(save_path):
        print(f"Error: File not found at {save_path}")
        return
        
    print(f"Starting ETL ingestion for: {save_path}")
    await process_file_background(
        save_path=save_path,
        out_filename=out_filename,
        client_id="test_script",
        username="test"
    )
    print("ETL ingestion complete! Data is now in PostgreSQL.")

if __name__ == "__main__":
    asyncio.run(main())
