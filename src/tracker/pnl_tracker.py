"""
PnL Tracker - Track profit/loss for wallets and tokens
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class Trade:
    tx_hash: str
    token_address: str
    token_symbol: str
    trade_type: str          # BUY or SELL
    amount_token: float
    amount_eth: float
    price_usd: float
    timestamp: datetime
    

@dataclass
class Position:
    token_address: str
    token_symbol: str
    amount: float
    avg_buy_price: float
    total_cost_eth: float
    current_value_eth: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    

@dataclass
class WalletPnL:
    address: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_invested_eth: float
    total_returned_eth: float
    realized_pnl_eth: float
    realized_pnl_percent: float
    unrealized_pnl_eth: float
    best_trade_eth: float
    worst_trade_eth: float
    avg_trade_pnl: float
    positions: List[Position] = field(default_factory=list)
    recent_trades: List[Trade] = field(default_factory=list)


class PnLTracker:
    def __init__(self):
        self.wallet_data: Dict[str, Dict] = {}
        self.trades: Dict[str, List[Trade]] = {}
        
    def record_trade(self, wallet: str, trade: Trade):
        """Record a new trade"""
        wallet = wallet.lower()
        
        if wallet not in self.trades:
            self.trades[wallet] = []
        
        self.trades[wallet].append(trade)
        self._update_wallet_stats(wallet)
    
    def _update_wallet_stats(self, wallet: str):
        """Update wallet statistics after a trade"""
        trades = self.trades.get(wallet, [])
        
        if not trades:
            return
        
        # Calculate positions
        positions = {}
        for trade in trades:
            token = trade.token_address
            
            if token not in positions:
                positions[token] = {
                    'symbol': trade.token_symbol,
                    'amount': 0,
                    'total_cost': 0,
                    'total_sold': 0
                }
            
            if trade.trade_type == 'BUY':
                positions[token]['amount'] += trade.amount_token
                positions[token]['total_cost'] += trade.amount_eth
            else:  # SELL
                positions[token]['amount'] -= trade.amount_token
                positions[token]['total_sold'] += trade.amount_eth
        
        self.wallet_data[wallet] = {
            'positions': positions,
            'trade_count': len(trades)
        }
    
    def get_wallet_pnl(self, wallet: str) -> WalletPnL:
        """Get full PnL report for a wallet"""
        wallet = wallet.lower()
        trades = self.trades.get(wallet, [])
        
        if not trades:
            return WalletPnL(
                address=wallet,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0,
                total_invested_eth=0,
                total_returned_eth=0,
                realized_pnl_eth=0,
                realized_pnl_percent=0,
                unrealized_pnl_eth=0,
                best_trade_eth=0,
                worst_trade_eth=0,
                avg_trade_pnl=0
            )
        
        # Calculate stats
        buys = [t for t in trades if t.trade_type == 'BUY']
        sells = [t for t in trades if t.trade_type == 'SELL']
        
        total_invested = sum(t.amount_eth for t in buys)
        total_returned = sum(t.amount_eth for t in sells)
        realized_pnl = total_returned - total_invested
        
        # Win/loss tracking per token
        token_pnl = {}
        for trade in trades:
            token = trade.token_address
            if token not in token_pnl:
                token_pnl[token] = {'cost': 0, 'returned': 0}
            
            if trade.trade_type == 'BUY':
                token_pnl[token]['cost'] += trade.amount_eth
            else:
                token_pnl[token]['returned'] += trade.amount_eth
        
        wins = sum(1 for t in token_pnl.values() if t['returned'] > t['cost'])
        losses = sum(1 for t in token_pnl.values() if t['returned'] < t['cost'])
        
        pnl_values = [t['returned'] - t['cost'] for t in token_pnl.values() if t['returned'] > 0]
        
        return WalletPnL(
            address=wallet,
            total_trades=len(trades),
            winning_trades=wins,
            losing_trades=losses,
            win_rate=(wins / len(token_pnl) * 100) if token_pnl else 0,
            total_invested_eth=total_invested,
            total_returned_eth=total_returned,
            realized_pnl_eth=realized_pnl,
            realized_pnl_percent=(realized_pnl / total_invested * 100) if total_invested > 0 else 0,
            unrealized_pnl_eth=0,  # Would need current prices
            best_trade_eth=max(pnl_values) if pnl_values else 0,
            worst_trade_eth=min(pnl_values) if pnl_values else 0,
            avg_trade_pnl=sum(pnl_values) / len(pnl_values) if pnl_values else 0,
            recent_trades=trades[-10:]  # Last 10 trades
        )
    
    def get_token_pnl(self, wallet: str, token: str) -> Dict:
        """Get PnL for specific token"""
        wallet = wallet.lower()
        token = token.lower()
        
        trades = [t for t in self.trades.get(wallet, []) if t.token_address.lower() == token]
        
        if not trades:
            return {'pnl': 0, 'trades': 0}
        
        cost = sum(t.amount_eth for t in trades if t.trade_type == 'BUY')
        returned = sum(t.amount_eth for t in trades if t.trade_type == 'SELL')
        
        return {
            'token': token,
            'trades': len(trades),
            'cost_eth': cost,
            'returned_eth': returned,
            'pnl_eth': returned - cost,
            'pnl_percent': ((returned - cost) / cost * 100) if cost > 0 else 0,
            'status': 'PROFIT' if returned > cost else 'LOSS' if returned < cost else 'NEUTRAL'
        }
    
    def format_pnl_message(self, pnl: WalletPnL) -> str:
        """Format PnL data for display"""
        pnl_sign = "+" if pnl.realized_pnl_eth >= 0 else ""
        
        return f"""
📊 **WALLET P&L REPORT**

👛 `{pnl.address[:10]}...{pnl.address[-8:]}`

**Performance:**
├ Total Trades: {pnl.total_trades}
├ Win Rate: {pnl.win_rate:.1f}%
├ Wins/Losses: {pnl.winning_trades}/{pnl.losing_trades}

**Profit & Loss:**
├ Invested: {pnl.total_invested_eth:.4f} ETH
├ Returned: {pnl.total_returned_eth:.4f} ETH
├ Realized P&L: {pnl_sign}{pnl.realized_pnl_eth:.4f} ETH ({pnl_sign}{pnl.realized_pnl_percent:.1f}%)

**Best/Worst:**
├ Best Trade: +{pnl.best_trade_eth:.4f} ETH
├ Worst Trade: {pnl.worst_trade_eth:.4f} ETH
├ Avg Trade: {pnl.avg_trade_pnl:.4f} ETH
"""
