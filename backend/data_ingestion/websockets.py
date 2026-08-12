import os
import io
import pandas as pd
import numpy as np
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.auth.auth_utils import add_log
from backend.database.database import SessionLocal
from backend.database.models import FileMetadata, CallMetric

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

manager = ConnectionManager()

@router.websocket('/ws/progress/{client_id}')
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(client_id)

async def process_file_background(save_path: str, out_filename: str, client_id: str, username: str):
    try:
        await manager.send_message({'status': 'processing', 'progress': 10, 'message': 'Parsing file...'}, client_id)
        await asyncio.sleep(0.5)
        
        if save_path.endswith('.csv'):
            df = pd.read_csv(save_path)
            df.columns = df.columns.str.strip()
        elif save_path.endswith('.xls') or save_path.endswith('.xlsx'):
            excel_file = pd.ExcelFile(save_path, engine='openpyxl')
            dfs = []
            for i, sheet_name in enumerate(excel_file.sheet_names):
                await manager.send_message({'status': 'processing', 'progress': 10 + int(40 * (i / len(excel_file.sheet_names))), 'message': f'Parsing sheet {sheet_name}...'}, client_id)
                sheet_df = pd.read_excel(excel_file, sheet_name=sheet_name)
                sheet_df.columns = sheet_df.columns.str.strip()
                if 'Company' not in sheet_df.columns:
                    sheet_df['Company'] = sheet_name
                dfs.append(sheet_df)
            df = pd.concat(dfs, ignore_index=True)
            
        await manager.send_message({'status': 'processing', 'progress': 60, 'message': 'Cleaning data...'}, client_id)
        df.dropna(how='all', inplace=True)
        df.dropna(axis=1, how='all', inplace=True)

        numeric_cols = df.select_dtypes(include='number').columns
        df[numeric_cols] = df[numeric_cols].fillna(0)
        
        await manager.send_message({'status': 'processing', 'progress': 75, 'message': 'Formatting columns...'}, client_id)
        object_cols = df.select_dtypes(include=['object', 'string']).columns
        df[object_cols] = df[object_cols].fillna('Unknown')
        for col in object_cols:
            df[col] = df[col].astype(str).str.strip()
            
        # Derived Quantities
        if 'ACD Calls in 20 Sec' in df.columns and 'Call Offered' in df.columns and 'ABAN Calls in 10 Sec' in df.columns:
            denom = (df['Call Offered'] - df['ABAN Calls in 10 Sec'])
            df['Service Level %'] = pd.Series(np.where(denom > 0, (df['ACD Calls in 20 Sec'] / denom) * 100, 0))
            df['Service Level Status'] = np.where(df['Service Level %'] > 85, 'Good', 'Penalty')
            
        if 'Hold Time' in df.columns and 'ACD Calls' in df.columns:
            df['Avg Hold Time'] = pd.Series(np.where(df['ACD Calls'] > 0, df['Hold Time'] / df['ACD Calls'], 0))
            df['Hold Time Status'] = np.where(df['Avg Hold Time'] <= 20, 'Good', 'Penalty')
            
        if 'ACD Time' in df.columns and 'ACW Time' in df.columns and 'Hold Time' in df.columns and 'ACD Calls' in df.columns:
            df['Avg Handle Time'] = pd.Series(np.where(df['ACD Calls'] > 0, (df['ACD Time'] + df['ACW Time'] + df['Hold Time']) / df['ACD Calls'], 0))
            df['AHT Status'] = np.where(df['Avg Handle Time'] <= 240, 'Good', 'Penalty')
            
        await manager.send_message({'status': 'processing', 'progress': 90, 'message': 'Inserting into database...'}, client_id)
        
        # Insert File Metadata
        with SessionLocal() as db:
            file_meta = FileMetadata(
                filename=out_filename,
                uploader=username,
                size_bytes=os.path.getsize(save_path)
            )
            db.add(file_meta)
            db.commit()
            db.refresh(file_meta)
            
            # Map df columns to db schema
            mapping = {
                'Company': 'company',
                'Language': 'language',
                'Date': 'date_logged',
                'Call Timestamp': 'call_timestamp',
                'Day': 'day',
                'Call Offered': 'call_offered',
                'ABAN Calls in 10 Sec': 'aban_calls_10_sec',
                'ACD Calls in 10 Sec': 'acd_calls_10_sec',
                'ACD Calls in 20 Sec': 'acd_calls_20_sec',
                'ABAN Calls': 'aban_calls',
                'Held Calls': 'held_calls',
                'Service Level %': 'service_level_pct',
                'Service Level Status': 'service_level_status',
                'ACD Calls': 'acd_calls',
                'Hold Time': 'hold_time',
                'Avg Hold Time': 'avg_hold_time',
                'Hold Time Status': 'hold_time_status',
                'ACD Time': 'acd_time',
                'ACW Time': 'acw_time',
                'Avg Handle Time': 'avg_handle_time',
                'AHT Status': 'aht_status'
            }
            
            df = df.rename(columns=mapping)
            available_cols = [col for col in mapping.values() if col in df.columns]
            
            # Convert to list of dicts for bulk insert
            records = df[available_cols].to_dict('records')
            
            # Inject file_id
            for record in records:
                record['file_id'] = file_meta.id
                
            # Bulk insert
            db.bulk_insert_mappings(CallMetric, records)
            
            add_log(db, 'FILE_UPLOADED', username, f'Uploaded and ingested file: {out_filename}')
            db.commit()
            
        await manager.send_message({'status': 'complete', 'progress': 100, 'message': 'Upload complete!'}, client_id)
    except Exception as e:
        await manager.send_message({'status': 'error', 'message': str(e)}, client_id)
