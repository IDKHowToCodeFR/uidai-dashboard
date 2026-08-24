import os
import io
import pandas as pd
import numpy as np
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.auth.auth_utils import add_log
from backend.database.database import SessionLocal
from backend.database.models import FileMetadata, CCFData
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

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

async def process_file_background(save_path: str, out_filename: str, client_id: str, username: str, data_type: str = "CCF Data", meta: dict = None):
    try:
        async def progress_callback(progress, message):
            await manager.send_message({'status': 'processing', 'progress': progress, 'message': message}, client_id)

        if data_type == "UniMate Data":
            from backend.data_ingestion.unimate_parser import UniMateParser
            from backend.database.repo import UniMateDatabaseRepo
            df = await UniMateParser.parse(save_path, progress_callback=progress_callback)
            
            await manager.send_message({'status': 'processing', 'progress': 90, 'message': 'Inserting into database...'}, client_id)
            with SessionLocal() as db:
                UniMateDatabaseRepo.save_parsed_data(
                    db=db, 
                    df=df, 
                    save_path=save_path, 
                    out_filename=out_filename, 
                    username=username, 
                    data_type=data_type, 
                    meta=meta
                )
        elif data_type == "CDR Data":
            from backend.data_ingestion.cdr_parser import CDRParser
            from backend.database.repo import CDRDatabaseRepo
            
            df = await CDRParser.parse(save_path, progress_callback=progress_callback)
            
            await manager.send_message({'status': 'processing', 'progress': 90, 'message': 'Inserting into database...'}, client_id)
            with SessionLocal() as db:
                CDRDatabaseRepo.save_parsed_data(
                    db=db, 
                    df=df, 
                    save_path=save_path, 
                    out_filename=out_filename, 
                    username=username, 
                    data_type=data_type, 
                    meta=meta
                )
        else:
            from backend.data_ingestion.ccf_parser import CCFParser
            from backend.database.repo import CCFDatabaseRepo
            
            # 1. Parse File (Pure Domain Module)
            df = await CCFParser.parse(save_path, progress_callback=progress_callback)
                
            # 2. Database Insert
            await manager.send_message({'status': 'processing', 'progress': 90, 'message': 'Inserting into database...'}, client_id)
            with SessionLocal() as db:
                CCFDatabaseRepo.save_parsed_data(
                    db=db, 
                    df=df, 
                    save_path=save_path, 
                    out_filename=out_filename, 
                    username=username, 
                    data_type=data_type, 
                    meta=meta
                )
            
        await manager.send_message({'status': 'complete', 'progress': 100, 'message': 'Upload complete!'}, client_id)
    except Exception as e:
        print("EXCEPTION OCCURRED:", e)
        await manager.send_message({'status': 'error', 'message': str(e)}, client_id)
