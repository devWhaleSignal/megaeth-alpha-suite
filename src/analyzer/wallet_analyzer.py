"""
Wallet Analyzer - Score wallets and label them (builder, farmer, sniper)
"""

from web3 import Web3
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class WalletLabel(Enum):
    BUILDER = "builder"      # Creates tokens, provides liquidity
    FARMER = "farmer"        # Farms airdrops, interacts with many protocols
    SNIPER = "sniper"        # Buys early, sells fast
    WHALE = "whale"          # High balance, big trades
    UNKNOWN = "unknown"


@dataclass
class WalletStats:
    address: str
    label: WalletLabel
    total_trades: int
    win_rate: float          # Percentage of profitable trades
    total_pnl: float         # Total profit/loss in ETH
    avg_hold_time: float     # Average hold time in hours
    tokens_deployed: int
    first_seen: str
    last_active: str
    confidence_score: int    # 0-100


class WalletAnalyzer:
    def __init__(self, config: dict):
        self.w3 = Web3(Web3.HTTPProvider(config['network']['rpc_url']))
        self.wallet_cache: Dict[str, WalletStats] = {}
        
    async def analyze_wallet(self, address: str) -> WalletStats:
        """Analyze a wallet and return its stats"""
        address = address.lower()
        
        if address in self.wallet_cache:
            return self.wallet_cache[address]
        
        # Get wallet data
        trades = await self.get_wallet_trades(address)
        deployed = await self.get_deployed_tokens(address)
        
        # Calculate stats
        total_trades = len(trades)
        wins = sum(1 for t in trades if t.get('profit', 0) > 0)
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        total_pnl = sum(t.get('profit', 0) for t in trades)
        
        # Calculate average hold time
        hold_times = [t.get('hold_time', 0) for t in trades if t.get('hold_time')]
        avg_hold_time = sum(hold_times) / len(hold_times) if hold_times else 0
        
        # Determine label
        label = self.determine_label(
            total_trades=total_trades,
            tokens_deployed=len(deployed),
            avg_hold_time=avg_hold_time,
            win_rate=win_rate
        )
        
        # Calculate confidence score
        confidence = self.calculate_confidence(
            total_trades=total_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            label=label
        )
        
        stats = WalletStats(
            address=address,
            label=label,
            total_trades=total_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            avg_hold_time=avg_hold_time,
            tokens_deployed=len(deployed),
            first_seen="",
            last_active="",
            confidence_score=confidence
        )
        
        self.wallet_cache[address] = stats
        return stats
    
    def determine_label(self, total_trades: int, tokens_deployed: int, 
                       avg_hold_time: float, win_rate: float) -> WalletLabel:
        """Determine wallet label based on behavior"""
        
        # Builder: deploys tokens
        if tokens_deployed >= 1:
            return WalletLabel.BUILDER
        
        # Sniper: quick trades, high win rate
        if avg_hold_time < 1 and win_rate > 60 and total_trades > 10:
            return WalletLabel.SNIPER
        
        # Farmer: many interactions, moderate hold time
        if total_trades > 50 and avg_hold_time > 24:
            return WalletLabel.FARMER
        
        # Whale: check balance
        # (simplified - would need balance check)
        if total_trades > 20 and win_rate > 50:
            return WalletLabel.WHALE
        
        return WalletLabel.UNKNOWN
    
    def calculate_confidence(self, total_trades: int, win_rate: float,
                            total_pnl: float, label: WalletLabel) -> int:
        """Calculate confidence score 0-100"""
        score = 50  # Base score
        
        # More trades = more confidence
        score += min(total_trades, 20)  # Up to +20
        
        # High win rate = more confidence
        if win_rate > 70:
            score += 15
        elif win_rate > 50:
            score += 10
        elif win_rate < 30:
            score -= 10
        
        # Profitable = more confidence
        if total_pnl > 10:
            score += 15
        elif total_pnl > 1:
            score += 10
        elif total_pnl < 0:
            score -= 10
        
        # Builders get bonus
        if label == WalletLabel.BUILDER:
            score += 5
        
        return max(0, min(100, score))
    
    async def get_wallet_trades(self, address: str) -> List[Dict]:
        """Get all trades for a wallet (placeholder)"""
        # In production, query blockchain/indexer for swap events
        return []
    
    async def get_deployed_tokens(self, address: str) -> List[str]:
        """Get tokens deployed by this wallet (placeholder)"""
        # In production, query for contract creations
        return []
    
    def get_label_emoji(self, label: WalletLabel) -> str:
        """Get emoji for wallet label"""
        emojis = {
            WalletLabel.BUILDER: "🏗️",
            WalletLabel.FARMER: "🌾",
            WalletLabel.SNIPER: "🎯",
            WalletLabel.WHALE: "🐋",
            WalletLabel.UNKNOWN: "❓"
        }
        return emojis.get(label, "❓")
