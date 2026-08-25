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

_active_connections: dict = {}

async def ws_connect(websocket: WebSocket, client_id: str):
    await websocket.accept()
    _active_connections[client_id] = websocket

def ws_disconnect(client_id: str):
    _active_connections.pop(client_id, None)

async def ws_send_message(message: dict, client_id: str):
    if client_id in _active_connections:
        await _active_connections[client_id].send_json(message)

@router.websocket('/ws/progress/{client_id}')
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await ws_connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_disconnect(client_id)

async def process_file_background(save_path: str, out_filename: str, client_id: str, username: str, data_type: str = "CCF Data", meta: dict = None):
    try:
        async def progress_callback(progress, message):
            await ws_send_message({'status': 'processing', 'progress': progress, 'message': message}, client_id)

        if data_type == "UniMate Data":
            from backend.data_ingestion.unimate_parser import parse_unimate
            from backend.database.repo import save_unimate_data
            df = await parse_unimate(save_path, progress_callback=progress_callback)
            
            await ws_send_message({'status': 'processing', 'progress': 90, 'message': 'Inserting into database...'}, client_id)
            with SessionLocal() as db:
                save_unimate_data(
                    db=db, 
                    df=df, 
                    save_path=save_path, 
                    out_filename=out_filename, 
                    username=username, 
                    data_type=data_type, 
                    meta=meta
                )
        elif data_type == "CDR Data":
            from backend.data_ingestion.cdr_parser import parse_cdr
            from backend.database.repo import save_cdr_data
            
            df = await parse_cdr(save_path, progress_callback=progress_callback)
            
            await ws_send_message({'status': 'processing', 'progress': 90, 'message': 'Inserting into database...'}, client_id)
            with SessionLocal() as db:
                save_cdr_data(
                    db=db, 
                    df=df, 
                    save_path=save_path, 
                    out_filename=out_filename, 
                    username=username, 
                    data_type=data_type, 
                    meta=meta
                )
        else:
            from backend.data_ingestion.ccf_parser import parse_ccf
            from backend.database.repo import save_ccf_data
            
            # 1. Parse File (Pure Domain Module)
            df = await parse_ccf(save_path, progress_callback=progress_callback)
                
            # 2. Database Insert
            await ws_send_message({'status': 'processing', 'progress': 90, 'message': 'Inserting into database...'}, client_id)
            with SessionLocal() as db:
                save_ccf_data(
                    db=db, 
                    df=df, 
                    save_path=save_path, 
                    out_filename=out_filename, 
                    username=username, 
                    data_type=data_type, 
                    meta=meta
                )
            
        await ws_send_message({'status': 'complete', 'progress': 100, 'message': 'Upload complete!'}, client_id)
    except Exception as e:
        print("EXCEPTION OCCURRED:", e)
        await ws_send_message({'status': 'error', 'message': str(e)}, client_id)
