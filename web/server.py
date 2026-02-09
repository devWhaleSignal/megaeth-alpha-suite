"""
MegaETH Alpha Suite - Web Dashboard
"""

import asyncio
import json
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Query
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
        self.wallet_stats: Dict[str, Dict] = {}  # Wallet analytics
        self.stats = {
            "tokens_scanned": 0,
            "trades_detected": 0,
            "arb_found": 0,
            "total_profit": 0.0,
            "wallets_tracked": 0
        }
    
    def add_token(self, token: Dict):
        token['timestamp'] = datetime.now().isoformat()
        # Add confidence score if not present
        if 'confidence_score' not in token:
            token['confidence_score'] = self._calc_token_score(token)
            token['risk_level'] = self._get_risk_level(token['confidence_score'])
        self.new_tokens.insert(0, token)
        self.new_tokens = self.new_tokens[:100]
        self.stats["tokens_scanned"] += 1
    
    def _calc_token_score(self, token: Dict) -> int:
        """Calculate token confidence score"""
        score = 50
        if token.get('liquidity_locked'): score += 20
        if token.get('ownership_renounced'): score += 15
        if token.get('verified'): score += 10
        if token.get('is_honeypot'): score -= 40
        if token.get('is_mintable'): score -= 10
        liq = token.get('liquidity_usd', 0)
        if liq >= 50000: score += 15
        elif liq >= 10000: score += 10
        elif liq < 1000: score -= 15
        return max(0, min(100, score))
    
    def _get_risk_level(self, score: int) -> str:
        if score >= 75: return "LOW"
        elif score >= 50: return "MEDIUM"
        elif score >= 25: return "HIGH"
        return "EXTREME"
    
    def add_trade(self, trade: Dict):
        trade['timestamp'] = datetime.now().isoformat()
        self.whale_trades.insert(0, trade)
        self.whale_trades = self.whale_trades[:100]
        self.stats["trades_detected"] += 1
        # Update wallet stats
        wallet = trade.get('wallet', '').lower()
        if wallet:
            self._update_wallet_stats(wallet, trade)
    
    def _update_wallet_stats(self, wallet: str, trade: Dict):
        """Update wallet statistics after a trade"""
        if wallet not in self.wallet_stats:
            self.wallet_stats[wallet] = {
                'address': wallet,
                'label': 'unknown',
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'total_pnl_eth': 0.0,
                'win_rate': 0.0,
                'confidence_score': 50,
                'first_seen': datetime.now().isoformat(),
                'last_active': datetime.now().isoformat()
            }
            self.stats['wallets_tracked'] += 1
        
        ws = self.wallet_stats[wallet]
        ws['total_trades'] += 1
        ws['last_active'] = datetime.now().isoformat()
        
        # Track PnL if available
        pnl = trade.get('pnl_eth', 0)
        ws['total_pnl_eth'] += pnl
        if pnl > 0:
            ws['wins'] += 1
        elif pnl < 0:
            ws['losses'] += 1
        
        # Update win rate
        total = ws['wins'] + ws['losses']
        ws['win_rate'] = (ws['wins'] / total * 100) if total > 0 else 0
        
        # Update label based on behavior
        ws['label'] = self._determine_wallet_label(ws)
        ws['confidence_score'] = self._calc_wallet_confidence(ws)
    
    def _determine_wallet_label(self, ws: Dict) -> str:
        """Determine wallet label"""
        if ws.get('is_deployer'): return "builder"
        if ws['total_trades'] > 50 and ws['win_rate'] > 60: return "sniper"
        if ws['total_pnl_eth'] > 10: return "whale"
        if ws['total_trades'] > 30: return "farmer"
        return "unknown"
    
    def _calc_wallet_confidence(self, ws: Dict) -> int:
        """Calculate wallet confidence score"""
        score = 50
        score += min(ws['total_trades'], 20)
        if ws['win_rate'] > 70: score += 15
        elif ws['win_rate'] > 50: score += 10
        elif ws['win_rate'] < 30: score -= 10
        if ws['total_pnl_eth'] > 10: score += 15
        elif ws['total_pnl_eth'] > 1: score += 10
        elif ws['total_pnl_eth'] < 0: score -= 10
        return max(0, min(100, score))
    
    def add_arbitrage(self, arb: Dict):
        arb['timestamp'] = datetime.now().isoformat()
        self.arbitrage_opportunities.insert(0, arb)
        self.arbitrage_opportunities = self.arbitrage_opportunities[:50]
        self.stats["arb_found"] += 1
    
    def get_filtered_tokens(self, min_score: int = 0, risk: str = None, 
                           liquidity_locked: bool = None, verified: bool = None) -> List[Dict]:
        """Get tokens with filters"""
        result = self.new_tokens
        if min_score > 0:
            result = [t for t in result if t.get('confidence_score', 0) >= min_score]
        if risk:
            result = [t for t in result if t.get('risk_level') == risk]
        if liquidity_locked is not None:
            result = [t for t in result if t.get('liquidity_locked') == liquidity_locked]
        if verified is not None:
            result = [t for t in result if t.get('verified') == verified]
        return result
    
    def get_wallet_leaderboard(self) -> List[Dict]:
        """Get wallets sorted by performance"""
        wallets = list(self.wallet_stats.values())
        return sorted(wallets, key=lambda x: x.get('total_pnl_eth', 0), reverse=True)[:20]

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

# Filtered tokens endpoint
@app.get("/api/tokens/filter")
async def get_filtered_tokens(
    min_score: int = Query(0, ge=0, le=100),
    risk: Optional[str] = Query(None),
    liquidity_locked: Optional[bool] = Query(None),
    verified: Optional[bool] = Query(None)
):
    return store.get_filtered_tokens(min_score, risk, liquidity_locked, verified)

# Wallet analytics endpoints
@app.get("/api/wallets")
async def get_wallets():
    return list(store.wallet_stats.values())

@app.get("/api/wallets/leaderboard")
async def get_leaderboard():
    return store.get_wallet_leaderboard()

@app.get("/api/wallet/{address}")
async def get_wallet(address: str):
    address = address.lower()
    if address in store.wallet_stats:
        return store.wallet_stats[address]
    return {"error": "Wallet not found"}

# Leaderboard page
@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(request: Request):
    return templates.TemplateResponse("leaderboard.html", {
        "request": request,
        "wallets": store.get_wallet_leaderboard()
    })

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
