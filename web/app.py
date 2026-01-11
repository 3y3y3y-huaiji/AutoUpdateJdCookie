from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List
import asyncio
import logging
from datetime import datetime
import uuid

from web.models import (
    AppConfig, AccountConfig, QinglongConfig, GlobalConfig,
    NotificationConfig, ProxyConfig, TaskStatus,
    AccountTestResult, QinglongTestResult
)
from config.settings import get_config_manager

app = FastAPI(title="AutoUpdateJdCookie Web管理", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_websockets: List[WebSocket] = []
task_status: dict = {}

log_queue = asyncio.Queue()

class LogHandler(logging.Handler):
    def emit(self, record):
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "message": self.format(record)
        }
        asyncio.create_task(log_queue.put(log_entry))

async def broadcast_logs():
    while True:
        log_entry = await log_queue.get()
        if active_websockets:
            disconnected = []
            for websocket in active_websockets:
                try:
                    await websocket.send_json(log_entry)
                except:
                    disconnected.append(websocket)
            for ws in disconnected:
                active_websockets.remove(ws)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_logs())

@app.get("/")
async def root():
    return HTMLResponse(content=open("web/static/index.html", "r", encoding="utf-8").read())

@app.get("/api/config")
async def get_config():
    try:
        config_manager = get_config_manager()
        config = config_manager.get_config()
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/config")
async def update_config(config: AppConfig):
    try:
        config_manager = get_config_manager()
        config_manager.update_config(config)
        return {"success": True, "message": "配置已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/accounts")
async def get_accounts():
    try:
        config_manager = get_config_manager()
        config = config_manager.get_config()
        return config.user_datas
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/accounts")
async def add_account(username: str, account: AccountConfig):
    try:
        config_manager = get_config_manager()
        config_manager.add_account(username, account)
        return {"success": True, "message": "账号已添加"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/accounts/{username}")
async def update_account(username: str, account: AccountConfig):
    try:
        config_manager = get_config_manager()
        config_manager.update_account(username, account)
        return {"success": True, "message": "账号已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/accounts/{username}")
async def delete_account(username: str):
    try:
        config_manager = get_config_manager()
        config_manager.remove_account(username)
        return {"success": True, "message": "账号已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/qinglong")
async def get_qinglong_config():
    try:
        config_manager = get_config_manager()
        config = config_manager.get_config()
        return config.qinglong_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/qinglong")
async def update_qinglong_config(config: QinglongConfig):
    try:
        config_manager = get_config_manager()
        config_manager.update_qinglong_config(config)
        return {"success": True, "message": "青龙面板配置已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/qinglong/test")
async def test_qinglong_connection():
    try:
        from api.qinglong import QlApi, QlOpenApi
        config_manager = get_config_manager()
        config = config_manager.get_config()
        ql_config = config.qinglong_data

        if ql_config.client_id and ql_config.client_secret:
            qlapi = QlOpenApi(ql_config.url)
            response = await qlapi.login(ql_config.client_id, ql_config.client_secret)
        elif ql_config.token:
            qlapi = QlApi(ql_config.url)
            qlapi.login_by_token(ql_config.token)
            response = await qlapi.get_envs()
        else:
            qlapi = QlApi(ql_config.url)
            response = await qlapi.login_by_username(ql_config.username, ql_config.password)
        if response.get('code') == 200:
            env_response = await qlapi.get_envs()
            return QinglongTestResult(
                success=True,
                message="连接成功",
                env_count=len(env_response.get('data', []))
            )
        else:
            return QinglongTestResult(
                success=False,
                message=f"连接失败: {response.get('message', '未知错误')}"
            )
    except Exception as e:
        return QinglongTestResult(success=False, message=f"连接失败: {str(e)}")

@app.get("/api/global")
async def get_global_config():
    try:
        config_manager = get_config_manager()
        config = config_manager.get_config()
        return config.global_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/global")
async def update_global_config(config: GlobalConfig):
    try:
        config_manager = get_config_manager()
        config_manager.update_global_config(config)
        return {"success": True, "message": "全局配置已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/notification")
async def get_notification_config():
    try:
        config_manager = get_config_manager()
        config = config_manager.get_config()
        return config.notification_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notification")
async def update_notification_config(config: NotificationConfig):
    try:
        config_manager = get_config_manager()
        config_manager.update_notification_config(config)
        return {"success": True, "message": "通知配置已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/proxy")
async def get_proxy_config():
    try:
        config_manager = get_config_manager()
        config = config_manager.get_config()
        return config.proxy_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/proxy")
async def update_proxy_config(config: ProxyConfig):
    try:
        config_manager = get_config_manager()
        config_manager.update_proxy_config(config)
        return {"success": True, "message": "代理配置已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/task/start")
async def start_task():
    try:
        task_id = str(uuid.uuid4())
        task_status[task_id] = TaskStatus(
            task_id=task_id,
            status="running",
            message="任务已启动",
            start_time=datetime.now().isoformat(),
            logs=[]
        )
        return {"success": True, "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/task/stop")
async def stop_task(task_id: str):
    try:
        if task_id in task_status:
            task_status[task_id].status = "pending"
            task_status[task_id].message = "任务已停止"
            task_status[task_id].end_time = datetime.now().isoformat()
            return {"success": True, "message": "任务已停止"}
        else:
            raise HTTPException(status_code=404, detail="任务不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/task/status/{task_id}")
async def get_task_status(task_id: str):
    if task_id in task_status:
        return task_status[task_id]
    else:
        raise HTTPException(status_code=404, detail="任务不存在")

@app.get("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_websockets.remove(websocket)