import os
import io
import pandas as pd
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.api.auth_utils import add_log, BASE_DIR

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

async def process_file_background(contents: bytes, safe_filename: str, save_path: str, client_id: str, username: str, out_filename: str):
    try:
        await manager.send_message({'status': 'processing', 'progress': 10, 'message': 'Parsing file...'}, client_id)
        await asyncio.sleep(0.5)
        
        if safe_filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
            df.columns = df.columns.str.strip()
        elif safe_filename.endswith('.xls') or safe_filename.endswith('.xlsx'):
            excel_file = pd.ExcelFile(io.BytesIO(contents), engine='openpyxl')
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
            
        await manager.send_message({'status': 'processing', 'progress': 90, 'message': 'Saving data...'}, client_id)
        df.to_csv(save_path, index=False)
        add_log('FILE_UPLOADED', username, f'Uploaded file: {out_filename}')
        
        await manager.send_message({'status': 'complete', 'progress': 100, 'message': 'Upload complete!'}, client_id)
    except Exception as e:
        await manager.send_message({'status': 'error', 'message': str(e)}, client_id)
