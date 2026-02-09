"""
Token Scorer - Calculate confidence score for new tokens
"""

from web3 import Web3
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class TokenScore:
    address: str
    name: str
    symbol: str
    confidence_score: int      # 0-100
    risk_level: str            # LOW, MEDIUM, HIGH, EXTREME
    
    # Individual scores
    liquidity_score: int
    holder_score: int
    contract_score: int
    deployer_score: int
    
    # Flags
    is_honeypot: bool
    is_mintable: bool
    has_blacklist: bool
    liquidity_locked: bool
    ownership_renounced: bool
    
    # Details
    liquidity_usd: float
    holder_count: int
    top_holder_percent: float
    deployer_history: int      # Number of previous tokens deployed


class TokenScorer:
    def __init__(self, config: dict):
        self.w3 = Web3(Web3.HTTPProvider(config['network']['rpc_url']))
        
    async def score_token(self, address: str, deployer: str = None) -> TokenScore:
        """Calculate comprehensive score for a token"""
        
        # Get all data
        liquidity = await self.get_liquidity(address)
        holders = await self.get_holder_data(address)
        contract = await self.analyze_contract(address)
        deployer_data = await self.analyze_deployer(deployer) if deployer else {}
        
        # Calculate individual scores
        liquidity_score = self.calc_liquidity_score(liquidity)
        holder_score = self.calc_holder_score(holders)
        contract_score = self.calc_contract_score(contract)
        deployer_score = self.calc_deployer_score(deployer_data)
        
        # Overall confidence
        confidence = int(
            liquidity_score * 0.25 +
            holder_score * 0.25 +
            contract_score * 0.30 +
            deployer_score * 0.20
        )
        
        # Risk level
        if confidence >= 75:
            risk = "LOW"
        elif confidence >= 50:
            risk = "MEDIUM"
        elif confidence >= 25:
            risk = "HIGH"
        else:
            risk = "EXTREME"
        
        return TokenScore(
            address=address,
            name=contract.get('name', 'Unknown'),
            symbol=contract.get('symbol', '???'),
            confidence_score=confidence,
            risk_level=risk,
            liquidity_score=liquidity_score,
            holder_score=holder_score,
            contract_score=contract_score,
            deployer_score=deployer_score,
            is_honeypot=contract.get('is_honeypot', False),
            is_mintable=contract.get('is_mintable', False),
            has_blacklist=contract.get('has_blacklist', False),
            liquidity_locked=liquidity.get('locked', False),
            ownership_renounced=contract.get('renounced', False),
            liquidity_usd=liquidity.get('usd', 0),
            holder_count=holders.get('count', 0),
            top_holder_percent=holders.get('top_percent', 100),
            deployer_history=deployer_data.get('token_count', 0)
        )
    
    def calc_liquidity_score(self, data: Dict) -> int:
        """Score based on liquidity"""
        usd = data.get('usd', 0)
        locked = data.get('locked', False)
        
        score = 0
        
        # Liquidity amount
        if usd >= 100000:
            score += 40
        elif usd >= 50000:
            score += 35
        elif usd >= 10000:
            score += 25
        elif usd >= 5000:
            score += 15
        elif usd >= 1000:
            score += 5
        
        # Locked liquidity bonus
        if locked:
            score += 60
        
        return min(100, score)
    
    def calc_holder_score(self, data: Dict) -> int:
        """Score based on holder distribution"""
        count = data.get('count', 0)
        top_percent = data.get('top_percent', 100)
        
        score = 0
        
        # Holder count
        if count >= 1000:
            score += 40
        elif count >= 500:
            score += 30
        elif count >= 100:
            score += 20
        elif count >= 50:
            score += 10
        
        # Distribution (lower top holder % is better)
        if top_percent <= 10:
            score += 60
        elif top_percent <= 20:
            score += 45
        elif top_percent <= 30:
            score += 30
        elif top_percent <= 50:
            score += 15
        
        return min(100, score)
    
    def calc_contract_score(self, data: Dict) -> int:
        """Score based on contract analysis"""
        score = 50  # Base
        
        # Penalties
        if data.get('is_honeypot'):
            score -= 50
        if data.get('is_mintable'):
            score -= 15
        if data.get('has_blacklist'):
            score -= 20
        if data.get('is_proxy'):
            score -= 10
        
        # Bonuses
        if data.get('renounced'):
            score += 25
        if data.get('verified'):
            score += 15
        if data.get('audited'):
            score += 30
        
        return max(0, min(100, score))
    
    def calc_deployer_score(self, data: Dict) -> int:
        """Score based on deployer history"""
        if not data:
            return 30  # Unknown deployer
        
        token_count = data.get('token_count', 0)
        success_rate = data.get('success_rate', 0)
        rugs = data.get('rugs', 0)
        
        score = 50
        
        # Experience
        if token_count >= 5 and rugs == 0:
            score += 25
        elif token_count >= 2 and rugs == 0:
            score += 15
        
        # Success rate
        if success_rate >= 80:
            score += 25
        elif success_rate >= 50:
            score += 10
        
        # Rug history
        if rugs > 0:
            score -= rugs * 20
        
        return max(0, min(100, score))
    
    async def get_liquidity(self, address: str) -> Dict:
        """Get token liquidity data (placeholder)"""
        return {'usd': 10000, 'locked': False}
    
    async def get_holder_data(self, address: str) -> Dict:
        """Get holder distribution data (placeholder)"""
        return {'count': 50, 'top_percent': 25}
    
    async def analyze_contract(self, address: str) -> Dict:
        """Analyze contract code (placeholder)"""
        return {
            'name': 'Unknown',
            'symbol': '???',
            'is_honeypot': False,
            'is_mintable': False,
            'has_blacklist': False,
            'is_proxy': False,
            'renounced': False,
            'verified': False,
            'audited': False
        }
    
    async def analyze_deployer(self, address: str) -> Dict:
        """Analyze deployer history (placeholder)"""
        return {
            'token_count': 0,
            'success_rate': 0,
            'rugs': 0
        }
    
    def get_risk_color(self, risk: str) -> str:
        """Get color for risk level"""
        colors = {
            'LOW': '#10b981',      # Green
            'MEDIUM': '#f59e0b',   # Orange
            'HIGH': '#ef4444',     # Red
            'EXTREME': '#7f1d1d'   # Dark red
        }
        return colors.get(risk, '#ffffff')
