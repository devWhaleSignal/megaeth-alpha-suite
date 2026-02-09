"""
MegaETH Alpha Suite - Web Dashboard
"""

import asyncio
import json
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Background scanner task
async def background_scanner():
    """Background task to scan for new tokens"""
    try:
        from web3 import Web3
    except ImportError:
        print("web3 not installed, scanner disabled")
        return
    
    config_path = Path(__file__).parent.parent / 'config' / 'settings.json'
    if not config_path.exists():
        print("Config not found, scanner disabled")
        return
    
    with open(config_path) as f:
        config = json.load(f)
    
    rpc_url = config['network']['rpc_url']
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        print(f"Cannot connect to RPC: {rpc_url}")
        return
    
    print(f"Scanner started - Chain ID: {w3.eth.chain_id}")
    last_block = w3.eth.block_number - 50  # Start from recent blocks
    
    # ERC20 ABI
    erc20_abi = [
        {'constant': True, 'inputs': [], 'name': 'name', 'outputs': [{'name': '', 'type': 'string'}], 'type': 'function'},
        {'constant': True, 'inputs': [], 'name': 'symbol', 'outputs': [{'name': '', 'type': 'string'}], 'type': 'function'},
        {'constant': True, 'inputs': [], 'name': 'decimals', 'outputs': [{'name': '', 'type': 'uint8'}], 'type': 'function'},
        {'constant': True, 'inputs': [], 'name': 'totalSupply', 'outputs': [{'name': '', 'type': 'uint256'}], 'type': 'function'}
    ]
    
    while True:
        try:
            current_block = w3.eth.block_number
            
            for block_num in range(last_block + 1, min(last_block + 10, current_block + 1)):
                try:
                    block = w3.eth.get_block(block_num, full_transactions=True)
                    
                    for tx in block.transactions:
                        if tx['to'] is None:  # Contract deployment
                            try:
                                receipt = w3.eth.get_transaction_receipt(tx['hash'])
                                contract_addr = receipt['contractAddress']
                                
                                if contract_addr:
                                    # Try to get token info
                                    contract = w3.eth.contract(address=contract_addr, abi=erc20_abi)
                                    
                                    try:
                                        name = contract.functions.name().call()
                                        symbol = contract.functions.symbol().call()
                                        decimals = contract.functions.decimals().call()
                                        total_supply = contract.functions.totalSupply().call()
                                        
                                        token = {
                                            'address': contract_addr,
                                            'name': name,
                                            'symbol': symbol,
                                            'decimals': decimals,
                                            'total_supply': str(total_supply),
                                            'deployer': tx['from'],
                                            'block': block_num,
                                            'tx_hash': tx['hash'].hex(),
                                            'liquidity_usd': 0,
                                            'has_liquidity': False
                                        }
                                        
                                        store.add_token(token)
                                        print(f"New token: {name} ({symbol}) at {contract_addr}")
                                        
                                        # Broadcast to WebSocket clients
                                        await manager.broadcast({"type": "new_token", "data": token})
                                    except:
                                        pass  # Not an ERC20
                            except:
                                pass
                except Exception as e:
                    print(f"Block scan error: {e}")
                    
            last_block = min(last_block + 10, current_block)
            await asyncio.sleep(2)  # Scan every 2 seconds
            
        except Exception as e:
            print(f"Scanner error: {e}")
            await asyncio.sleep(5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background scanner
    scanner_task = asyncio.create_task(background_scanner())
    yield
    # Cleanup
    scanner_task.cancel()

# App setup
app = FastAPI(title="MegaETH Alpha Suite", version="1.0.0", lifespan=lifespan)

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

# Scanner page
@app.get("/scanner", response_class=HTMLResponse)
async def scanner_page(request: Request):
    return templates.TemplateResponse("scanner.html", {"request": request})

# Token lookup endpoint
@app.get("/api/token/{address}")
async def lookup_token(address: str):
    """Lookup any token by address directly from blockchain"""
    from web3 import Web3
    import json
    
    try:
        with open('config/settings.json') as f:
            config = json.load(f)
        
        w3 = Web3(Web3.HTTPProvider(config['network']['rpc_url']))
        
        if not w3.is_connected():
            return {"error": "RPC not connected"}
        
        # Check if contract exists
        code = w3.eth.get_code(address)
        if len(code) == 0:
            return {"error": "Contract not found", "address": address}
        
        # ERC20 ABI
        abi = [
            {'constant': True, 'inputs': [], 'name': 'name', 'outputs': [{'name': '', 'type': 'string'}], 'type': 'function'},
            {'constant': True, 'inputs': [], 'name': 'symbol', 'outputs': [{'name': '', 'type': 'string'}], 'type': 'function'},
            {'constant': True, 'inputs': [], 'name': 'decimals', 'outputs': [{'name': '', 'type': 'uint8'}], 'type': 'function'},
            {'constant': True, 'inputs': [], 'name': 'totalSupply', 'outputs': [{'name': '', 'type': 'uint256'}], 'type': 'function'},
            {'constant': True, 'inputs': [], 'name': 'owner', 'outputs': [{'name': '', 'type': 'address'}], 'type': 'function'}
        ]
        
        contract = w3.eth.contract(address=w3.to_checksum_address(address), abi=abi)
        
        try:
            name = contract.functions.name().call()
        except:
            name = "Unknown"
        
        try:
            symbol = contract.functions.symbol().call()
        except:
            symbol = "???"
        
        try:
            decimals = contract.functions.decimals().call()
        except:
            decimals = 18
        
        try:
            total_supply = contract.functions.totalSupply().call()
            total_supply_formatted = total_supply / (10 ** decimals)
        except:
            total_supply = 0
            total_supply_formatted = 0
        
        try:
            owner = contract.functions.owner().call()
        except:
            owner = None
        
        return {
            "address": address,
            "name": name,
            "symbol": symbol,
            "decimals": decimals,
            "total_supply": str(total_supply),
            "total_supply_formatted": total_supply_formatted,
            "owner": owner,
            "contract_size": len(code),
            "chain_id": w3.eth.chain_id
        }
        
    except Exception as e:
        return {"error": str(e)}

# Full token scan endpoint with holder analysis
@app.get("/api/scan/{address}")
async def scan_token(address: str):
    """Full token scan with holders, flags, and safety score"""
    from web3 import Web3
    import json
    
    try:
        config_path = Path(__file__).parent.parent / 'config' / 'settings.json'
        with open(config_path) as f:
            config = json.load(f)
        
        w3 = Web3(Web3.HTTPProvider(config['network']['rpc_url']))
        
        if not w3.is_connected():
            return {"error": "Cannot connect to MegaETH RPC"}
        
        address = w3.to_checksum_address(address)
        
        # Check if contract exists
        code = w3.eth.get_code(address)
        if len(code) == 0:
            return {"error": "Contract not found at this address"}
        
        # Extended ERC20 ABI
        abi = [
            {'constant': True, 'inputs': [], 'name': 'name', 'outputs': [{'name': '', 'type': 'string'}], 'type': 'function'},
            {'constant': True, 'inputs': [], 'name': 'symbol', 'outputs': [{'name': '', 'type': 'string'}], 'type': 'function'},
            {'constant': True, 'inputs': [], 'name': 'decimals', 'outputs': [{'name': '', 'type': 'uint8'}], 'type': 'function'},
            {'constant': True, 'inputs': [], 'name': 'totalSupply', 'outputs': [{'name': '', 'type': 'uint256'}], 'type': 'function'},
            {'constant': True, 'inputs': [], 'name': 'owner', 'outputs': [{'name': '', 'type': 'address'}], 'type': 'function'},
            {'constant': True, 'inputs': [{'name': '', 'type': 'address'}], 'name': 'balanceOf', 'outputs': [{'name': '', 'type': 'uint256'}], 'type': 'function'},
        ]
        
        contract = w3.eth.contract(address=address, abi=abi)
        
        # Get basic info
        try:
            name = contract.functions.name().call()
        except:
            name = "Unknown"
        
        try:
            symbol = contract.functions.symbol().call()
        except:
            symbol = "???"
        
        try:
            decimals = contract.functions.decimals().call()
        except:
            decimals = 18
        
        try:
            total_supply = contract.functions.totalSupply().call()
            total_supply_formatted = total_supply / (10 ** decimals)
        except:
            total_supply = 0
            total_supply_formatted = 0
        
        try:
            owner = contract.functions.owner().call()
            if owner == "0x0000000000000000000000000000000000000000":
                owner = None
        except:
            owner = None
        
        # Try to find deployer from recent transactions (simplified)
        deployer = None
        try:
            # Get creation tx from explorer API if available
            pass
        except:
            pass
        
        # Analyze top holders by checking Transfer events
        top_holders = []
        dev_percent = 0
        
        try:
            # Get Transfer event signature
            transfer_topic = w3.keccak(text="Transfer(address,address,uint256)").hex()
            
            # Get recent transfer logs
            logs = w3.eth.get_logs({
                'address': address,
                'topics': [transfer_topic],
                'fromBlock': max(0, w3.eth.block_number - 5000),
                'toBlock': 'latest'
            })
            
            # Track balances from transfers
            balances = {}
            for log in logs:
                from_addr = '0x' + log['topics'][1].hex()[-40:]
                to_addr = '0x' + log['topics'][2].hex()[-40:]
                value = int(log['data'].hex(), 16)
                
                if from_addr != '0x0000000000000000000000000000000000000000':
                    balances[from_addr] = balances.get(from_addr, 0) - value
                balances[to_addr] = balances.get(to_addr, 0) + value
            
            # Sort by balance
            sorted_holders = sorted(balances.items(), key=lambda x: x[1], reverse=True)[:10]
            
            for addr, balance in sorted_holders:
                if balance > 0 and total_supply > 0:
                    percent = (balance / total_supply) * 100
                    label = None
                    
                    # Check if it's a contract (LP, etc)
                    holder_code = w3.eth.get_code(w3.to_checksum_address(addr))
                    if len(holder_code) > 0:
                        label = "contract"
                    
                    # Check if it's the owner/deployer
                    if owner and addr.lower() == owner.lower():
                        label = "dev"
                        dev_percent = percent
                    
                    top_holders.append({
                        "address": addr,
                        "percent": percent,
                        "label": label
                    })
        except Exception as e:
            print(f"Holder analysis error: {e}")
        
        # Build security flags
        flags = []
        safety_score = 50  # Start neutral
        
        # Owner check
        if owner is None:
            flags.append({"text": "Ownership renounced", "good": True})
            safety_score += 15
        else:
            flags.append({"text": "Owner can modify contract", "warn": True})
            safety_score -= 10
        
        # Contract size check
        if len(code) < 500:
            flags.append({"text": "Very small contract (possible proxy)", "warn": True})
            safety_score -= 5
        elif len(code) > 20000:
            flags.append({"text": "Large contract (complex logic)", "neutral": True})
        else:
            flags.append({"text": "Normal contract size", "good": True})
            safety_score += 5
        
        # Dev holdings check
        if dev_percent > 50:
            flags.append({"text": f"Dev holds {dev_percent:.1f}% - HIGH RISK", "bad": True})
            safety_score -= 30
        elif dev_percent > 20:
            flags.append({"text": f"Dev holds {dev_percent:.1f}%", "warn": True})
            safety_score -= 15
        elif dev_percent > 0:
            flags.append({"text": f"Dev holds {dev_percent:.1f}%", "neutral": True})
        else:
            flags.append({"text": "Dev wallet not identified", "neutral": True})
        
        # Top holder concentration
        if top_holders:
            top1_percent = top_holders[0]['percent'] if top_holders else 0
            if top1_percent > 50:
                flags.append({"text": f"Top holder owns {top1_percent:.1f}%", "bad": True})
                safety_score -= 20
            elif top1_percent > 20:
                flags.append({"text": f"Top holder owns {top1_percent:.1f}%", "warn": True})
                safety_score -= 10
            else:
                flags.append({"text": "Good holder distribution", "good": True})
                safety_score += 10
        
        # Supply check
        if total_supply_formatted > 1e15:
            flags.append({"text": "Extremely high supply", "warn": True})
        elif total_supply_formatted < 1000:
            flags.append({"text": "Very low supply", "neutral": True})
        else:
            flags.append({"text": "Normal supply range", "good": True})
            safety_score += 5
        
        # Clamp score
        safety_score = max(0, min(100, safety_score))
        
        return {
            "address": address,
            "name": name,
            "symbol": symbol,
            "decimals": decimals,
            "total_supply": str(total_supply),
            "total_supply_formatted": total_supply_formatted,
            "owner": owner,
            "deployer": deployer,
            "contract_size": len(code),
            "chain_id": w3.eth.chain_id,
            "top_holders": top_holders,
            "dev_percent": dev_percent,
            "flags": flags,
            "safety_score": safety_score
        }
        
    except Exception as e:
        return {"error": str(e)}

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
