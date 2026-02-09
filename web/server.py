"""
MegaETH Alpha Suite - Web Dashboard
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# App setup
app = FastAPI(title="MegaETH Alpha Suite", version="1.0.0")

# Static files and templates
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# In-memory data store (replace with database for production)
class DataStore:
    def __init__(self):
        self.new_tokens: List[Dict] = []
        self.whale_trades: List[Dict] = []
        self.arbitrage_opportunities: List[Dict] = []
        self.tracked_wallets: List[Dict] = []
        self.stats = {
            "tokens_scanned": 0,
            "trades_detected": 0,
            "arb_found": 0,
            "total_profit": 0.0
        }
    
    def add_token(self, token: Dict):
        token['timestamp'] = datetime.now().isoformat()
        self.new_tokens.insert(0, token)
        self.new_tokens = self.new_tokens[:100]  # Keep last 100
        self.stats["tokens_scanned"] += 1
    
    def add_trade(self, trade: Dict):
        trade['timestamp'] = datetime.now().isoformat()
        self.whale_trades.insert(0, trade)
        self.whale_trades = self.whale_trades[:100]
        self.stats["trades_detected"] += 1
    
    def add_arbitrage(self, arb: Dict):
        arb['timestamp'] = datetime.now().isoformat()
        self.arbitrage_opportunities.insert(0, arb)
        self.arbitrage_opportunities = self.arbitrage_opportunities[:50]
        self.stats["arb_found"] += 1

store = DataStore()

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "stats": store.stats
    })

@app.get("/tokens", response_class=HTMLResponse)
async def tokens_page(request: Request):
    return templates.TemplateResponse("tokens.html", {
        "request": request,
        "tokens": store.new_tokens
    })

@app.get("/whales", response_class=HTMLResponse)
async def whales_page(request: Request):
    return templates.TemplateResponse("whales.html", {
        "request": request,
        "trades": store.whale_trades
    })

@app.get("/arbitrage", response_class=HTMLResponse)
async def arbitrage_page(request: Request):
    return templates.TemplateResponse("arbitrage.html", {
        "request": request,
        "opportunities": store.arbitrage_opportunities
    })

# API endpoints
@app.get("/api/stats")
async def get_stats():
    return store.stats

@app.get("/api/tokens")
async def get_tokens():
    return store.new_tokens

@app.get("/api/trades")
async def get_trades():
    return store.whale_trades

@app.get("/api/arbitrage")
async def get_arbitrage():
    return store.arbitrage_opportunities

@app.post("/api/token")
async def add_token(token: dict):
    store.add_token(token)
    await manager.broadcast({"type": "new_token", "data": token})
    return {"status": "ok"}

@app.post("/api/trade")
async def add_trade(trade: dict):
    store.add_trade(trade)
    await manager.broadcast({"type": "new_trade", "data": trade})
    return {"status": "ok"}

@app.post("/api/arb")
async def add_arb(arb: dict):
    store.add_arbitrage(arb)
    await manager.broadcast({"type": "new_arb", "data": arb})
    return {"status": "ok"}

# WebSocket for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Run server
def run_server(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    run_server()
